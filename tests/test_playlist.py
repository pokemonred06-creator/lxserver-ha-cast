"""Unit tests for the playback queue."""

from __future__ import annotations

import importlib.util
import pathlib
import random
import sys
import unittest

_PKG = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "lxserver_cast"
_spec = importlib.util.spec_from_file_location("_lxcast_playlist", _PKG / "playlist.py")
assert _spec is not None and _spec.loader is not None
playlist = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = playlist
_spec.loader.exec_module(playlist)


class PlaybackQueueTests(unittest.TestCase):
    def test_yields_items_in_order_then_none(self) -> None:
        queue = playlist.PlaybackQueue(["a", "b", "c"])
        self.assertEqual([queue.next(), queue.next(), queue.next(), queue.next()], ["a", "b", "c", None])
        self.assertEqual(queue.remaining, 0)

    def test_shuffle_keeps_every_item_once(self) -> None:
        queue = playlist.PlaybackQueue(range(10), shuffle=True, rng=random.Random(7))
        drawn = [queue.next() for _ in range(10)]
        self.assertEqual(sorted(drawn), list(range(10)))
        self.assertNotEqual(drawn, list(range(10)))

    def test_remaining_counts_down(self) -> None:
        queue = playlist.PlaybackQueue([1, 2])
        self.assertEqual(queue.remaining, 2)
        queue.next()
        self.assertEqual(queue.remaining, 1)


if __name__ == "__main__":
    unittest.main()
