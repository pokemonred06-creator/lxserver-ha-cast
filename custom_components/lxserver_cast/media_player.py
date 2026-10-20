"""LX Server media player: browse lxserver and send playback to the default Cast device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.components.media_player.browse_media import BrowseMedia
from homeassistant.components.media_player.const import MediaClass
from homeassistant.components.media_player.errors import BrowseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import LxRuntime, device_info
from .const import BROWSE_SOURCE, CONF_VOLUME, DEFAULT_VOLUME, DOMAIN, MAX_PLAYLIST_TRACKS
from .lxserver import LxServerError
from .media import FAVORITES_ID, FOLDER_TYPE, PLAYLIST_TYPE, POPULAR_ID, TRACK_TYPE, parse_media, track_id

_STATE_MAP = {
    "playing": MediaPlayerState.PLAYING,
    "buffering": MediaPlayerState.BUFFERING,
    "paused": MediaPlayerState.PAUSED,
    "idle": MediaPlayerState.IDLE,
    "off": MediaPlayerState.OFF,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([LxServerMediaPlayer(entry)])


def _folder(content_id: str, title: str) -> BrowseMedia:
    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_type=FOLDER_TYPE,
        media_content_id=content_id,
        title=title,
        can_play=False,
        can_expand=True,
    )


def _listing(content_id: str, title: str, children: list[BrowseMedia]) -> BrowseMedia:
    return BrowseMedia(
        media_class=MediaClass.DIRECTORY,
        media_content_type=FOLDER_TYPE,
        media_content_id=content_id,
        title=title,
        can_play=False,
        can_expand=True,
        children=children,
        children_media_class=MediaClass.PLAYLIST,
    )


def _playlist(source: str, list_id: str, title: str, thumbnail: str | None = None) -> BrowseMedia:
    return BrowseMedia(
        media_class=MediaClass.PLAYLIST,
        media_content_type=PLAYLIST_TYPE,
        media_content_id=f"{source}:{list_id}",
        title=title,
        can_play=True,
        can_expand=True,
        thumbnail=thumbnail,
    )


async def _playlist_node(runtime: LxRuntime, source: str, list_id: str) -> BrowseMedia:
    songs = await runtime.client.songlist_tracks(source, list_id)
    children: list[BrowseMedia] = []
    for index, song in enumerate(songs[:MAX_PLAYLIST_TRACKS]):
        name = str(song.get("name") or "Track")
        singer = song.get("singer")
        children.append(
            BrowseMedia(
                media_class=MediaClass.TRACK,
                media_content_type=TRACK_TYPE,
                media_content_id=track_id(source, list_id, index),
                title=f"{name} - {singer}" if singer else name,
                can_play=True,
                can_expand=False,
                thumbnail=song.get("img"),
            )
        )
    return BrowseMedia(
        media_class=MediaClass.PLAYLIST,
        media_content_type=PLAYLIST_TYPE,
        media_content_id=f"{source}:{list_id}",
        title="Tracks",
        can_play=True,
        can_expand=True,
        children=children,
        children_media_class=MediaClass.TRACK,
    )


async def _browse(runtime: LxRuntime, content_type: str | None, content_id: str | None) -> BrowseMedia:
    if not content_id:
        children = []
        if runtime.favorites:
            children.append(_folder(FAVORITES_ID, "Favorites"))
        children.append(_folder(POPULAR_ID, "Popular playlists"))
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_type=FOLDER_TYPE,
            media_content_id="",
            title="LX Server",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.DIRECTORY,
        )
    if content_type == PLAYLIST_TYPE:
        request = parse_media(PLAYLIST_TYPE, content_id)
        return await _playlist_node(runtime, request.source, request.list_id)
    if content_id == FAVORITES_ID:
        return _listing(FAVORITES_ID, "Favorites", [_playlist(f.source, f.list_id, f.name) for f in runtime.favorites])
    if content_id == POPULAR_ID:
        items = await runtime.client.popular_playlists(BROWSE_SOURCE)
        children = [
            _playlist(BROWSE_SOURCE, str(item["id"]), str(item.get("name") or "Playlist"), item.get("img"))
            for item in items
            if item.get("id")
        ]
        return _listing(POPULAR_ID, "Popular playlists", children)
    raise BrowseError(f"Unknown LX Server item: {content_id}")


class LxServerMediaPlayer(MediaPlayerEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:music-box-multiple"
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry_id = entry.entry_id
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = device_info(entry.entry_id)
        self._attr_volume_level = float(entry.options.get(CONF_VOLUME, DEFAULT_VOLUME))

    def _runtime(self) -> LxRuntime | None:
        return self.hass.data.get(DOMAIN, {}).get(self._entry_id)

    def _require_runtime(self) -> LxRuntime:
        runtime = self._runtime()
        if runtime is None:
            raise ServiceValidationError("LX Server Cast is not loaded")
        return runtime

    @staticmethod
    def _require_target(runtime: LxRuntime) -> str:
        if not runtime.default_target:
            raise ServiceValidationError("Choose a default Cast device in the integration options")
        return runtime.default_target

    @property
    def available(self) -> bool:
        # Browsing works without a Cast target. Only playback needs one.
        return self._runtime() is not None

    @property
    def state(self) -> MediaPlayerState:
        runtime = self._runtime()
        target = runtime.default_target if runtime else None
        device = self.hass.states.get(target) if target else None
        if device is None:
            return MediaPlayerState.OFF
        return _STATE_MAP.get(device.state, MediaPlayerState.OFF)

    @property
    def media_title(self) -> str | None:
        runtime = self._runtime()
        if runtime is None or not runtime.default_target:
            return None
        player = runtime.players.get(runtime.default_target)
        return player.current_title if player else None

    async def async_added_to_hass(self) -> None:
        runtime = self._runtime()
        if runtime and runtime.default_target:
            self.async_on_remove(
                async_track_state_change_event(self.hass, [runtime.default_target], self._on_target_change)
            )

    @callback
    def _on_target_change(self, event: Event) -> None:
        self.async_write_ha_state()

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        runtime = self._runtime()
        if runtime is None:
            raise BrowseError("LX Server Cast is not loaded")
        try:
            return await _browse(runtime, media_content_type, media_content_id)
        except (LxServerError, ValueError) as err:
            raise BrowseError(str(err)) from err

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        runtime = self._require_runtime()
        target = self._require_target(runtime)
        try:
            request = parse_media(media_type, media_id)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        volume = self.volume_level if self.volume_level is not None else runtime.default_volume
        await runtime.play(request, target, volume)
        self.async_write_ha_state()

    async def _forward(self, service: str) -> None:
        runtime = self._require_runtime()
        target = self._require_target(runtime)
        await self.hass.services.async_call("media_player", service, {"entity_id": target}, blocking=True)

    async def async_media_play(self) -> None:
        await self._forward("media_play")
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        await self._forward("media_pause")
        self.async_write_ha_state()

    async def async_media_next_track(self) -> None:
        runtime = self._require_runtime()
        await runtime.player_for(self._require_target(runtime)).skip()
        self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        runtime = self._require_runtime()
        await runtime.player_for(self._require_target(runtime)).stop()
        self.async_write_ha_state()

    async def async_set_volume_level(self, volume: float) -> None:
        runtime = self._require_runtime()
        target = self._require_target(runtime)
        self._attr_volume_level = volume
        await self.hass.services.async_call(
            "media_player", "volume_set", {"entity_id": target, "volume_level": volume}, blocking=True
        )
        self.async_write_ha_state()
