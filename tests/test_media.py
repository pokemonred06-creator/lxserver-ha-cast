"""Unit tests for media request parsing."""

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


if __name__ == "__main__":
    unittest.main()
