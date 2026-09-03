"""In-memory cache for parsed device configurations."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class ConfigCache:
    """TTL-based cache for parsed configs.

    Key: relative_path of the config file.
    Value: (parsed_data_dict, timestamp).

    Cache miss: parse fresh.
    Cache hit but stale: parse fresh.
    """

    def __init__(self, ttl_seconds: int = 300):
        """ttl_seconds: 5 minutes by default per ТЗ §6."""
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if present and fresh."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, ts = entry
        if (time.time() - ts) > self.ttl_seconds:
            # expired
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value with current timestamp."""
        self._store[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        """Drop a specific cache entry."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Drop all entries."""
        self._store.clear()

    def size(self) -> int:
        """Number of entries currently cached."""
        return len(self._store)
