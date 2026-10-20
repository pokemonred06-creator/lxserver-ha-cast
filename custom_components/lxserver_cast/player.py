"""Plays lxserver tracks one after another on a Cast-capable media player."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .lxserver import LxServerClient, LxServerError, Song, mime_for_quality
from .playlist import PlaybackQueue

_LOGGER = logging.getLogger(__name__)

_ACTIVE_STATES = {"playing", "buffering", "paused"}
_FINISHED_STATES = {"idle", "off"}


class CastQueuePlayer:
    """One queue per target. Each track gets a fresh stream grant when it starts."""

    def __init__(self, hass: HomeAssistant, client: LxServerClient, target: str, quality: str) -> None:
        self._hass = hass
        self._client = client
        self._target = target
        self._quality = quality
        self._queue: PlaybackQueue[Song] | None = None
        self._grant_id: str | None = None
        self._unsubscribe: Callable[[], None] | None = None

    async def start(self, songs: list[Song], *, shuffle: bool, volume: float) -> None:
        await self.release()
        self._queue = PlaybackQueue(songs, shuffle=shuffle)
        self._unsubscribe = async_track_state_change_event(self._hass, [self._target], self._on_state_change)
        await self._call("media_player", "volume_set", {"entity_id": self._target, "volume_level": volume})
        await self._play_next()

    async def stop(self) -> None:
        await self.release()
        await self._call("media_player", "media_stop", {"entity_id": self._target})

    async def release(self) -> None:
        """Stop advancing and revoke the current grant. Does not touch playback."""
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._queue = None
        grant_id, self._grant_id = self._grant_id, None
        if grant_id is not None:
            await self._client.revoke_grant(grant_id)

    @callback
    def _on_state_change(self, event: Event) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if old_state is None or new_state is None:
            return
        if old_state.state in _ACTIVE_STATES and new_state.state in _FINISHED_STATES:
            self._hass.async_create_task(self._advance())

    async def _advance(self) -> None:
        try:
            await self._play_next()
        except Exception:
            _LOGGER.exception("Could not advance playback on %s", self._target)

    async def _play_next(self) -> None:
        queue = self._queue
        while queue is not None and self._queue is queue:
            song = queue.next()
            if song is None:
                _LOGGER.info("Finished the queue on %s", self._target)
                await self.release()
                return
            try:
                grant_id, url = await self._client.cast_stream(song, self._quality)
            except LxServerError as err:
                _LOGGER.warning("Skipping %s: %s", song.get("name", "track"), err)
                continue
            previous, self._grant_id = self._grant_id, grant_id
            if previous is not None:
                await self._client.revoke_grant(previous)
            await self._call(
                "media_player",
                "play_media",
                {
                    "entity_id": self._target,
                    "media_content_id": url,
                    "media_content_type": mime_for_quality(self._quality),
                },
            )
            return

    async def _call(self, domain: str, service: str, data: dict[str, Any]) -> None:
        await self._hass.services.async_call(domain, service, data, blocking=True)
