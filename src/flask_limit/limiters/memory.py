from time import time

from .base import Limiter


class MemRateLimiter(Limiter):
    """Rate limiter that uses a Python dictionary as storage."""

    def __init__(self):
        self.counters = {}

    def is_allowed(self, key, limit, period):
        now = int(time())
        begin_period = now // period * period
        end_period = begin_period + period

        self.cleanup(now)
        if key in self.counters:
            self.counters[key]["hits"] += 1
        else:
            self.counters[key] = {"hits": 1, "reset": end_period}
        allow = True
        remaining = limit - self.counters[key]["hits"]
        if remaining < 0:
            remaining = 0
            allow = False
        return allow, remaining, self.counters[key]["reset"]

    def cleanup(self, now):
        for key, value in list(self.counters.items()):
            if value["reset"] < now:
                del self.counters[key]
