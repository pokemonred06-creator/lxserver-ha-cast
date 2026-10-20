"""Ordered playback queue. Pure Python so it can be unit tested."""

from __future__ import annotations

import random
from collections.abc import Iterable
from typing import Generic, TypeVar

T = TypeVar("T")


class PlaybackQueue(Generic[T]):
    """Hands out items in order, shuffled once at creation when requested."""

    def __init__(self, items: Iterable[T], *, shuffle: bool = False, rng: random.Random | None = None) -> None:
        self._items: list[T] = list(items)
        if shuffle:
            (rng or random.Random()).shuffle(self._items)
        self._position = 0

    @property
    def remaining(self) -> int:
        return len(self._items) - self._position

    def next(self) -> T | None:
        if self._position >= len(self._items):
            return None
        item = self._items[self._position]
        self._position += 1
        return item
