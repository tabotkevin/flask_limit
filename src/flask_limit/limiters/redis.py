from time import time

from .base import Limiter


class RedisRateLimiter(Limiter):
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
