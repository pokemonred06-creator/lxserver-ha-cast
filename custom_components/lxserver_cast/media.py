"""Parses media_player.play_media requests. Pure Python so it can be unit tested."""

from __future__ import annotations

from dataclasses import dataclass

PLAYLIST_TYPE = "playlist"
SEARCH_TYPES = frozenset({"music", "track", "search"})


@dataclass(frozen=True)
class PlaylistRequest:
    source: str
    list_id: str


@dataclass(frozen=True)
class SearchRequest:
    query: str


def parse_media(media_type: str | None, media_id: str) -> PlaylistRequest | SearchRequest:
    value = (media_id or "").strip()
    if not value:
        raise ValueError("Enter a playlist ID or a search phrase")
    if media_type == PLAYLIST_TYPE:
        source, sep, list_id = value.partition(":")
        source, list_id = source.strip(), list_id.strip()
        if not sep or not source or not list_id:
            raise ValueError("Playlist IDs look like wy:17879848678 (source:id)")
        return PlaylistRequest(source, list_id)
    if not media_type or media_type in SEARCH_TYPES:
        return SearchRequest(value)
    raise ValueError(f"Unsupported media type: {media_type}")
