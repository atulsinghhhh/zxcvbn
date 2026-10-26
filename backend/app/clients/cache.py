"""Thread-safe in-memory TTL + LRU cache for upstream responses.

The Elexon clients are synchronous and called concurrently from a thread
pool, so the cache guards all access with a lock. Entries expire after a
fixed TTL; when the cache is full, the least-recently-used entry is evicted.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Generic, TypeVar

_V = TypeVar("_V")


class TTLCache(Generic[_V]):
    """Bounded cache mapping string keys to values with per-entry expiry."""

    def __init__(self, ttl_seconds: float, max_entries: int) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max(1, max_entries)
        self._lock = threading.Lock()
        # key -> (expires_at_monotonic, value); ordered by recency of use.
        self._store: OrderedDict[str, tuple[float, _V]] = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self._ttl > 0

    def get(self, key: str) -> _V | None:
        """Return the cached value for *key*, or None if missing/expired."""
        if not self.enabled:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: _V) -> None:
        """Store *value* under *key*, evicting the oldest entry if full."""
        if not self.enabled:
            return
        expires_at = time.monotonic() + self._ttl
        with self._lock:
            self._store[key] = (expires_at, value)
            self._store.move_to_end(key)
            while len(self._store) > self._max_entries:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
