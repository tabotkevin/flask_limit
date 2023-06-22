from abc import ABC, abstractmethod
from time import time


class Limiter(ABC):
    @abstractmethod
    def is_allowed(self, key, limit, period):
        """Check if the client's request should be allowed, based on the
        hit counter. Returns a 3-element tuple with a True/False result,
        the number of remaining hits in the period, and the time the
        counter resets for the next period."""
        pass

    @abstractmethod
    def cleanup(self, key=None):
        """Eliminate expired keys."""
        pass


class MemRateLimit(Limiter):
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


class RedisRateLimit(Limiter):
    """Rate limiter that uses a Redis as storage."""

    def __init__(self, client):
        self.client = client

    def is_allowed(self, key, limit, period):
        now = int(time())
        begin_period = now // period * period
        end_period = begin_period + period

        self.cleanup(now, key)
        if self.client.hlen(key):
            hits = int(self.client.hget(key, "hits"))
            self.client.hset(key, "hits", hits + 1)
        else:
            self.client.hset(key, mapping={"hits": 1, "reset": end_period})
        allow = True
        remaining = limit - int(self.client.hget(key, "hits"))
        if remaining < 0:
            remaining = 0
            allow = False
        return allow, remaining, int(self.client.hget(key, "reset"))

    def cleanup(self, now, key):
        reset = self.client.hget(key, "reset")
        if reset and int(reset) < now:
            self.client.delete(key)
