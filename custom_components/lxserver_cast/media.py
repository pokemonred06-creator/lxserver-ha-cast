"""Parses media requests and favorite playlists. Pure Python so it can be unit tested."""

from __future__ import annotations

from dataclasses import dataclass

PLAYLIST_TYPE = "playlist"
TRACK_TYPE = "lxserver_track"
FOLDER_TYPE = "lxserver_folder"
SEARCH_TYPES = frozenset({"music", "track", "search"})

FAVORITES_ID = "favorites"
POPULAR_ID = "popular"


@dataclass(frozen=True)
class PlaylistRequest:
    source: str
    list_id: str


@dataclass(frozen=True)
class TrackRequest:
    """A track inside a playlist. Playback runs from that track to the end of the list."""

    source: str
    list_id: str
    index: int


@dataclass(frozen=True)
class SearchRequest:
    query: str


@dataclass(frozen=True)
class Favorite:
    name: str
    source: str
    list_id: str


def split_ref(ref: str) -> tuple[str, str]:
    """Split `source:playlist_id` into its two parts."""
    source, sep, list_id = ref.partition(":")
    source, list_id = source.strip(), list_id.strip()
    if not sep or not source or not list_id:
        raise ValueError(f"Playlist IDs look like wy:17879848678, not {ref!r}")
    return source, list_id


def track_id(source: str, list_id: str, index: int) -> str:
    return f"{source}:{list_id}:{index}"


def parse_media(media_type: str | None, media_id: str) -> PlaylistRequest | TrackRequest | SearchRequest:
    value = (media_id or "").strip()
    if not value:
        raise ValueError("Enter a playlist ID or a search phrase")
    if media_type == PLAYLIST_TYPE:
        source, list_id = split_ref(value)
        return PlaylistRequest(source, list_id)
    if media_type == TRACK_TYPE:
        head, sep, index = value.rpartition(":")
        if not sep or not index.isdigit():
            raise ValueError(f"Track IDs look like wy:17879848678:0, not {value!r}")
        source, list_id = split_ref(head)
        return TrackRequest(source, list_id, int(index))
    if not media_type or media_type in SEARCH_TYPES:
        return SearchRequest(value)
    raise ValueError(f"Unsupported media type: {media_type}")


def parse_favorites(text: str | None) -> list[Favorite]:
    """One favorite per line: `Name | source:playlist_id`, or a bare `source:playlist_id`."""
    favorites: list[Favorite] = []
    seen: set[tuple[str, str]] = set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, ref = line.partition("|")
        if not sep:
            name, ref = "", line
        source, list_id = split_ref(ref.strip())
        if (source, list_id) in seen:
            continue
        seen.add((source, list_id))
        favorites.append(Favorite(name.strip() or list_id, source, list_id))
    return favorites
