"""Unit tests for media request parsing and favorite playlists."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

_PKG = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "lxserver_cast"
_spec = importlib.util.spec_from_file_location("_lxcast_media", _PKG / "media.py")
assert _spec is not None and _spec.loader is not None
media = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = media
_spec.loader.exec_module(media)


class ParseMediaTests(unittest.TestCase):
    def test_playlist_id_splits_source_and_id(self) -> None:
        self.assertEqual(media.parse_media("playlist", "wy:17879848678"), media.PlaylistRequest("wy", "17879848678"))

    def test_playlist_without_source_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_media("playlist", "17879848678")

    def test_playlist_with_empty_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_media("playlist", "wy:")

    def test_track_id_selects_index(self) -> None:
        self.assertEqual(media.parse_media("lxserver_track", "wy:123:4"), media.TrackRequest("wy", "123", 4))

    def test_track_id_helper_round_trips(self) -> None:
        parsed = media.parse_media(media.TRACK_TYPE, media.track_id("wy", "9", 0))
        self.assertEqual(parsed, media.TrackRequest("wy", "9", 0))

    def test_track_without_index_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_media("lxserver_track", "wy:123")

    def test_track_with_non_numeric_index_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_media("lxserver_track", "wy:123:x")

    def test_music_is_a_trimmed_search(self) -> None:
        self.assertEqual(media.parse_media("music", "  Mozart K467 "), media.SearchRequest("Mozart K467"))

    def test_missing_type_is_a_search(self) -> None:
        self.assertEqual(media.parse_media(None, "lullaby"), media.SearchRequest("lullaby"))

    def test_unknown_type_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_media("video", "x")

    def test_empty_media_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_media("music", "   ")


class FavoritesTests(unittest.TestCase):
    def test_named_and_bare_lines(self) -> None:
        favorites = media.parse_favorites("Bedtime | wy:17879848678\n# comment\n\nwy:42")
        self.assertEqual(
            favorites,
            [media.Favorite("Bedtime", "wy", "17879848678"), media.Favorite("42", "wy", "42")],
        )

    def test_duplicates_are_dropped(self) -> None:
        self.assertEqual(len(media.parse_favorites("wy:1\nA | wy:1")), 1)

    def test_bad_reference_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            media.parse_favorites("Bedtime | 17879848678")

    def test_empty_text_is_empty_list(self) -> None:
        self.assertEqual(media.parse_favorites(""), [])


if __name__ == "__main__":
    unittest.main()
