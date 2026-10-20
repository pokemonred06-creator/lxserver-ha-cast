"""Async client for the lxserver HTTP API.

This module has no Home Assistant imports so it can be unit tested directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

Song = dict[str, Any]
SEARCH_SOURCES = {
    "song": ("kw", "wy", "tx", "kg", "mg"),
    "artist": ("wy", "tx"),
    "playlist": ("wy",),
}


class LxServerError(Exception):
    """lxserver was unreachable, rejected a request, or returned an unusable response."""


class LxServerAuthError(LxServerError):
    """The username or password was rejected."""


class LxQueueFullError(LxServerError):
    """An enqueue request would exceed the upcoming-track limit."""


class Transport(Protocol):
    """Sends one request and returns (HTTP status, parsed JSON or None)."""

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[int, Any]: ...


def mime_for_quality(quality: str) -> str:
    return "audio/flac" if quality.startswith("flac") else "audio/mpeg"


def _songs(status: int, data: Any, what: str) -> list[Song]:
    if status != 200 or not isinstance(data, dict):
        raise LxServerError(f"Could not load {what} (HTTP {status})")
    items = data.get("list")
    if not isinstance(items, list):
        raise LxServerError(f"Invalid {what} response")
    return [item for item in items if isinstance(item, dict)]


class LxServerClient:
    """Logs in once, reuses the session token, and logs in again when it expires."""

    def __init__(self, transport: Transport, base_url: str, username: str, password: str) -> None:
        self._transport = transport
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._token: str | None = None

    async def login(self) -> None:
        status, data = await self._transport.request(
            "POST",
            "/api/user/login",
            json={"username": self._username, "password": self._password},
        )
        if status in (400, 401):
            raise LxServerAuthError("Invalid username or password")
        if status != 200 or not isinstance(data, dict) or not data.get("token"):
            raise LxServerError(f"Login failed (HTTP {status})")
        self._token = str(data["token"])

    async def _send(self, method: str, path: str, params: Mapping[str, Any] | None, body: Any) -> tuple[int, Any]:
        headers = {"x-user-token": self._token or "", "x-user-name": self._username}
        return await self._transport.request(method, path, params=params, json=body, headers=headers)

    async def _authed(
        self, method: str, path: str, *, params: Mapping[str, Any] | None = None, body: Any = None
    ) -> tuple[int, Any]:
        if self._token is None:
            await self.login()
        status, data = await self._send(method, path, params, body)
        if status == 401:
            await self.login()
            status, data = await self._send(method, path, params, body)
        return status, data

    async def search(self, query: str, *, source: str = "kw", limit: int = 3, kind: str = "song") -> list[Song]:
        if source not in SEARCH_SOURCES.get(kind, ()):
            raise LxServerError("This source does not support the selected search type")
        status, data = await self._authed(
            "GET",
            "/api/music/search",
            params={"name": query, "source": source, "type": "singer" if kind == "artist" else kind, "limit": limit, "page": 1},
        )
        return _songs(status, data, f"search for {query!r}")

    async def artist_tracks(self, source: str, artist_id: str) -> list[Song]:
        if source not in SEARCH_SOURCES["artist"]:
            raise LxServerError("This source does not support artists")
        status, data = await self._authed(
            "GET", "/api/music/artistSongs", params={"source": source, "id": artist_id, "order": "hot"}
        )
        if status != 200 or not isinstance(data, list):
            raise LxServerError(f"Could not load artist tracks (HTTP {status})")
        return [song for song in data if isinstance(song, dict)]

    async def songlist_tracks(self, source: str, list_id: str) -> list[Song]:
        status, data = await self._authed(
            "GET",
            "/api/music/songList/detail",
            params={"source": source, "id": list_id, "page": 1},
        )
        return _songs(status, data, f"playlist {list_id}")

    async def popular_playlists(self, source: str, *, page: int = 1) -> list[Song]:
        status, data = await self._authed(
            "GET",
            "/api/music/songList/list",
            params={"source": source, "sortId": "hot", "tagId": "", "page": page},
        )
        return _songs(status, data, "popular playlists")

    async def stream_url(self, song: Song, quality: str) -> str:
        status, data = await self._authed(
            "POST",
            "/api/music/url",
            body={
                "songInfo": song,
                "quality": quality,
                "enableAutoSwitchApiSource": True,
                "excludeApiSources": [],
            },
        )
        url = data.get("url") if isinstance(data, dict) else None
        if status != 200 or not isinstance(url, str) or not url:
            raise LxServerError(f"No playable URL for {song.get('name', 'track')} (HTTP {status})")
        return url

    async def create_grant(self, upstream_url: str, quality: str) -> tuple[str, str]:
        """Return (grant id, absolute media URL the Cast device can fetch)."""
        status, data = await self._authed(
            "POST",
            "/api/music/cast/session",
            body={"url": upstream_url, "mime": mime_for_quality(quality)},
        )
        if status != 200 or not isinstance(data, dict) or not data.get("id") or not data.get("url"):
            raise LxServerError(f"Cast grant failed (HTTP {status})")
        return str(data["id"]), f"{self._base_url}{data['url']}"

    async def cast_stream(self, song: Song, quality: str) -> tuple[str, str]:
        upstream = await self.stream_url(song, quality)
        return await self.create_grant(upstream, quality)

    async def revoke_grant(self, grant_id: str) -> None:
        """Best effort. Grants also expire on their own."""
        try:
            await self._authed("DELETE", "/api/music/cast/session", params={"id": grant_id})
        except LxServerError:
            pass
