from threading import RLock
from time import time

from .base import Limiter


class MemRateLimiter(Limiter, name="memory"):
    """Rate limiter backed by process-local memory.

    This backend is thread-safe within a single Python process.

    It is not shared between multiple processes or application instances.
    """

    def __init__(self):
        self.counters: dict[str, dict[str, int]] = {}
        self._lock = RLock()

    @classmethod
    def from_app(cls, app):
        return cls()

    def is_allowed(
        self,
        key: str,
        limit: int,
        period: int,
    ) -> tuple[bool, int, int]:
        now = int(time())

        begin_period = now // period * period
        end_period = begin_period + period

        with self._lock:
            counter = self.counters.get(key)

            # Start a new window if this is the first request or
            # the previous window has expired.
            if counter is None or counter["reset"] <= now:
                counter = {
                    "hits": 1,
                    "reset": end_period,
                }

                self.counters[key] = counter
            else:
                counter["hits"] += 1

            hits = counter["hits"]

            allowed = hits <= limit
            remaining = max(0, limit - hits)

            return allowed, remaining, counter["reset"]

    def cleanup(self, key: str | None = None):

        now = int(time())

        with self._lock:
            if key is not None:
                counter = self.counters.get(key)

                if counter and counter["reset"] <= now:
                    del self.counters[key]

                return

            expired_keys = [
                counter_key
                for counter_key, counter in self.counters.items()
                if counter["reset"] <= now
            ]

            for counter_key in expired_keys:
                del self.counters[counter_key]
