"""LX Server media player. Sends playback to the default Cast device."""

from __future__ import annotations

from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import LxRuntime
from .const import CONF_VOLUME, DEFAULT_SEARCH_SOURCE, DEFAULT_VOLUME, DOMAIN
from .media import PlaylistRequest, parse_media

_STATE_MAP = {
    "playing": MediaPlayerState.PLAYING,
    "buffering": MediaPlayerState.BUFFERING,
    "paused": MediaPlayerState.PAUSED,
    "idle": MediaPlayerState.IDLE,
    "off": MediaPlayerState.OFF,
}
_MAX_PLAYLIST_TRACKS = 200


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([LxServerMediaPlayer(entry)])


class LxServerMediaPlayer(MediaPlayerEntity):
    _attr_name = "LX Server"
    _attr_icon = "mdi:music-box-multiple"
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
    )

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry_id = entry.entry_id
        self._attr_unique_id = entry.entry_id
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
        runtime = self._runtime()
        return runtime is not None and bool(runtime.default_target)

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

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        runtime = self._require_runtime()
        target = self._require_target(runtime)
        try:
            request = parse_media(media_type, media_id)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        if isinstance(request, PlaylistRequest):
            songs = await runtime.client.songlist_tracks(request.source, request.list_id)
            songs = songs[:_MAX_PLAYLIST_TRACKS]
        else:
            songs = (await runtime.client.search(request.query, source=DEFAULT_SEARCH_SOURCE))[:1]
        if not songs:
            raise ServiceValidationError("lxserver returned no tracks for that request")
        volume = self.volume_level if self.volume_level is not None else runtime.default_volume
        await runtime.player_for(target).start(songs, shuffle=False, volume=volume)
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
