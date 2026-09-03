"""TTL cache invalidated by file metadata changes."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class CacheEntry(Generic[T]):
    value: T
    stored_at: float
    mtime_ns: int
    size: int


class ParsedConfigCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 300) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry[T]] = {}

    def get(self, key: str, *, mtime_ns: int, size: int) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expired = time.monotonic() - entry.stored_at > self.ttl_seconds
        changed = entry.mtime_ns != mtime_ns or entry.size != size
        if expired or changed:
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: T, *, mtime_ns: int, size: int) -> None:
        self._entries[key] = CacheEntry(value, time.monotonic(), mtime_ns, size)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
