"""LX Server Cast: browse lxserver and queue its tracks on a Google Cast media player."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    ATTR_LIMIT,
    ATTR_LIST_ID,
    ATTR_QUERIES,
    ATTR_SEARCH_SOURCE,
    ATTR_SHUFFLE,
    ATTR_SOURCE,
    ATTR_TARGET,
    ATTR_VOLUME,
    CONF_FAVORITES,
    CONF_PASSWORD,
    CONF_QUALITY,
    CONF_TARGET,
    CONF_URL,
    CONF_USERNAME,
    CONF_VOLUME,
    DEFAULT_FAVORITES,
    DEFAULT_QUALITY,
    DEFAULT_SEARCH_SOURCE,
    DEFAULT_VOLUME,
    DOMAIN,
    MAX_PLAYLIST_TRACKS,
    SERVICE_PLAY_SONGLIST,
    SERVICE_PLAY_TRACKS,
    SERVICE_STOP,
)
from .lxserver import LxServerClient, Song
from .media import Favorite, PlaylistRequest, SearchRequest, TrackRequest, parse_favorites
from .player import CastQueuePlayer
from .transport import AiohttpTransport

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.BUTTON]

_VOLUME = vol.All(vol.Coerce(float), vol.Range(min=0, max=1))

PLAY_SONGLIST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_SOURCE, default="wy"): cv.string,
        vol.Required(ATTR_LIST_ID): cv.string,
        vol.Optional(ATTR_TARGET): cv.entity_id,
        vol.Optional(ATTR_VOLUME): _VOLUME,
        vol.Optional(ATTR_SHUFFLE, default=False): cv.boolean,
        vol.Optional(ATTR_LIMIT, default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
    }
)

PLAY_TRACKS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_QUERIES): vol.All(cv.ensure_list, [cv.string], vol.Length(min=1, max=50)),
        vol.Optional(ATTR_SEARCH_SOURCE, default=DEFAULT_SEARCH_SOURCE): cv.string,
        vol.Optional(ATTR_TARGET): cv.entity_id,
        vol.Optional(ATTR_VOLUME): _VOLUME,
        vol.Optional(ATTR_SHUFFLE, default=False): cv.boolean,
    }
)

STOP_SCHEMA = vol.Schema({vol.Optional(ATTR_TARGET): cv.entity_id})

PlayRequest = PlaylistRequest | TrackRequest | SearchRequest


@dataclass
class LxRuntime:
    """State for one configured lxserver, shared by the services and entities."""

    hass: HomeAssistant
    client: LxServerClient
    default_target: str | None
    default_volume: float
    quality: str
    favorites: list[Favorite] = field(default_factory=list)
    players: dict[str, CastQueuePlayer] = field(default_factory=dict)
    ui_tracks: dict[str, Song] = field(default_factory=dict)

    def player_for(self, target: str) -> CastQueuePlayer:
        from homeassistant.helpers import entity_registry as er

        entity = er.async_get(self.hass).async_get(target)
        if entity is not None and entity.platform == DOMAIN:
            raise ServiceValidationError("Choose an output device, not the LX Server player")
        if target not in self.players:
            self.players[target] = CastQueuePlayer(self.hass, self.client, target, self.quality)
        return self.players[target]

    async def resolve(self, request: PlayRequest) -> list[Song]:
        if isinstance(request, SearchRequest):
            return (await self.client.search(request.query, source=DEFAULT_SEARCH_SOURCE))[:1]
        songs = await self.client.songlist_tracks(request.source, request.list_id)
        start = request.index if isinstance(request, TrackRequest) else 0
        return songs[start : start + MAX_PLAYLIST_TRACKS]

    async def play(self, request: PlayRequest, target: str, volume: float) -> None:
        songs = await self.resolve(request)
        if not songs:
            raise ServiceValidationError("lxserver returned no tracks for that request")
        await self.player_for(target).start(songs, shuffle=False, volume=volume)


def device_info(entry_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="LX Server",
        manufacturer="LX Music",
        model="lxserver",
    )


def _runtime(hass: HomeAssistant) -> LxRuntime:
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if not runtimes:
        raise ServiceValidationError("LX Server Cast is not configured")
    return runtimes[0]


def _target(runtime: LxRuntime, call: ServiceCall) -> str:
    target = call.data.get(ATTR_TARGET) or runtime.default_target
    if not target:
        raise ServiceValidationError("Choose a media player or set a default in the integration options")
    return target


async def _start(runtime: LxRuntime, call: ServiceCall, songs: list[Song]) -> None:
    await runtime.player_for(_target(runtime, call)).start(
        songs,
        shuffle=call.data[ATTR_SHUFFLE],
        volume=call.data.get(ATTR_VOLUME, runtime.default_volume),
    )


async def _handle_play_songlist(call: ServiceCall) -> None:
    runtime = _runtime(call.hass)
    songs = await runtime.client.songlist_tracks(call.data[ATTR_SOURCE], call.data[ATTR_LIST_ID])
    songs = songs[: call.data[ATTR_LIMIT]]
    if not songs:
        raise ServiceValidationError("lxserver returned no tracks for this playlist")
    await _start(runtime, call, songs)


async def _handle_play_tracks(call: ServiceCall) -> None:
    runtime = _runtime(call.hass)
    songs: list[Song] = []
    for query in call.data[ATTR_QUERIES]:
        matches = await runtime.client.search(query, source=call.data[ATTR_SEARCH_SOURCE])
        if matches:
            songs.append(matches[0])
        else:
            _LOGGER.warning("No lxserver match for %r", query)
    if not songs:
        raise ServiceValidationError("None of the queries matched a track")
    await _start(runtime, call, songs)


async def _handle_stop(call: ServiceCall) -> None:
    runtime = _runtime(call.hass)
    await runtime.player_for(_target(runtime, call)).stop()


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    from .panel import async_setup_panel

    await async_setup_panel(hass)
    hass.services.async_register(DOMAIN, SERVICE_PLAY_SONGLIST, _handle_play_songlist, schema=PLAY_SONGLIST_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_PLAY_TRACKS, _handle_play_tracks, schema=PLAY_TRACKS_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, _handle_stop, schema=STOP_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    url = entry.data[CONF_URL]
    client = LxServerClient(
        AiohttpTransport(async_get_clientsession(hass), url),
        url,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    options = entry.options
    try:
        favorites = parse_favorites(options.get(CONF_FAVORITES, DEFAULT_FAVORITES))
    except ValueError as err:
        _LOGGER.warning("Ignoring favorite playlists: %s", err)
        favorites = []
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = LxRuntime(
        hass=hass,
        client=client,
        default_target=options.get(CONF_TARGET) or None,
        default_volume=float(options.get(CONF_VOLUME, DEFAULT_VOLUME)),
        quality=options.get(CONF_QUALITY, DEFAULT_QUALITY),
        favorites=favorites,
    )
    entry.async_on_unload(entry.add_update_listener(_reload_on_change))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    options = entry.options
    if runtime and (
        options.get(CONF_QUALITY, DEFAULT_QUALITY) == runtime.quality
        and float(options.get(CONF_VOLUME, DEFAULT_VOLUME)) == runtime.default_volume
        and parse_favorites(options.get(CONF_FAVORITES, DEFAULT_FAVORITES)) == runtime.favorites
    ):
        runtime.default_target = options.get(CONF_TARGET) or None
        async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_target")
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    runtime = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime is not None:
        for player in runtime.players.values():
            await player.release()
    return True
