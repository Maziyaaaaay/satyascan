import time
from collections import defaultdict
from functools import lru_cache
from threading import Lock
from typing import Dict, List

from app.config import get_settings


class RateLimitExceeded(Exception):
    def __init__(self, key: str):
        super().__init__(f"Rate limit exceeded for {key}")
        self.key = key


class InMemoryRateLimiter:
    """Sliding-window limiter: at most `limit` calls per `window_seconds` per
    key. Single-process only, which is fine for the MVP's single Compose
    replica - swap for a Redis-backed implementation if scaled horizontally."""

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self._limit = limit
        self._window_seconds = window_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self._window_seconds
            while hits and hits[0] < cutoff:
                hits.pop(0)
            if len(hits) >= self._limit:
                raise RateLimitExceeded(key)
            hits.append(now)


@lru_cache
def get_rate_limiter() -> InMemoryRateLimiter:
    settings = get_settings()
    return InMemoryRateLimiter(limit=settings.rate_limit_per_minute, window_seconds=60.0)


def reset_rate_limiter_for_tests() -> None:
    get_rate_limiter.cache_clear()
