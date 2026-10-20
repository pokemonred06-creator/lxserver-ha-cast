"""Buttons for LX Server Cast: next track, stop, and one button per favorite playlist."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LxRuntime, device_info
from .const import CONF_FAVORITES, DEFAULT_FAVORITES, DOMAIN
from .media import Favorite, PlaylistRequest, parse_favorites


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    try:
        favorites = parse_favorites(entry.options.get(CONF_FAVORITES, DEFAULT_FAVORITES))
    except ValueError:
        favorites = []
    entities: list[ButtonEntity] = [
        LxControlButton(entry, "next_track", "Next track", "mdi:skip-next"),
        LxControlButton(entry, "stop", "Stop playback", "mdi:stop"),
    ]
    entities.extend(LxFavoriteButton(entry, favorite) for favorite in favorites)
    async_add_entities(entities)


def _loaded_runtime(hass: HomeAssistant, entry_id: str) -> tuple[LxRuntime, str]:
    runtime: LxRuntime | None = hass.data.get(DOMAIN, {}).get(entry_id)
    if runtime is None:
        raise ServiceValidationError("LX Server Cast is not loaded")
    if not runtime.default_target:
        raise ServiceValidationError("Choose a default Cast device in the integration options")
    return runtime, runtime.default_target


class _LxButtonBase(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry_id = entry.entry_id
        self._attr_device_info = device_info(entry.entry_id)


class LxControlButton(_LxButtonBase):
    def __init__(self, entry: ConfigEntry, key: str, name: str, icon: str) -> None:
        super().__init__(entry)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"

    async def async_press(self) -> None:
        runtime, target = _loaded_runtime(self.hass, self._entry_id)
        player = runtime.player_for(target)
        if self._key == "stop":
            await player.stop()
        else:
            await player.skip()


class LxFavoriteButton(_LxButtonBase):
    def __init__(self, entry: ConfigEntry, favorite: Favorite) -> None:
        super().__init__(entry)
        self._favorite = favorite
        self._attr_name = favorite.name
        self._attr_icon = "mdi:playlist-play"
        self._attr_unique_id = f"{entry.entry_id}_{favorite.source}_{favorite.list_id}"

    async def async_press(self) -> None:
        runtime, target = _loaded_runtime(self.hass, self._entry_id)
        request = PlaylistRequest(self._favorite.source, self._favorite.list_id)
        await runtime.play(request, target, runtime.default_volume)
