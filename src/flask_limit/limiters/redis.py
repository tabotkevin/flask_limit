from time import time

from .base import Limiter, LimiterException


class RedisRateLimiter(Limiter, name="redis"):

    _SCRIPT = """
    local key = KEYS[1]

    local now = tonumber(ARGV[1])
    local limit = tonumber(ARGV[2])
    local end_period = tonumber(ARGV[3])
    local ttl = tonumber(ARGV[4])

    local hits = redis.call("HGET", key, "hits")
    local reset = redis.call("HGET", key, "reset")

    -- Start a new rate-limit window.
    if not hits or not reset or tonumber(reset) <= now then

        hits = 1
        reset = end_period

        redis.call(
            "HSET",
            key,
            "hits",
            hits,
            "reset",
            reset
        )

    else

        hits = tonumber(hits) + 1

        redis.call(
            "HSET",
            key,
            "hits",
            hits
        )

    end

    -- Make sure Redis removes the key after the window.
    redis.call("EXPIRE", key, ttl)

    local remaining = limit - hits

    if remaining < 0 then
        remaining = 0
    end

    local allowed = 0

    if hits <= limit then
        allowed = 1
    end

    return {
        allowed,
        remaining,
        reset
    }
    """

    def __init__(self, client):
        self.client = client
        self._script = self.client.register_script(self._SCRIPT)

    @classmethod
    def from_app(cls, app):
        try:
            import redis
        except ImportError as exc:
            raise LimiterException(
                "Redis support requires the 'redis' package. "
                "Install it with: pip install flask_limit[redis]"
            ) from exc

        redis_url = app.config["RATELIMIT_REDIS_URL"]
        client = redis.Redis.from_url(redis_url, decode_responses=False)

        return cls(client)

    def is_allowed(
        self,
        key: str,
        limit: int,
        period: int,
    ) -> tuple[bool, int, int]:
        now = int(time())

        begin_period = now // period * period
        end_period = begin_period + period

        result = self._script(
            keys=[key],
            args=[
                now,
                limit,
                end_period,
                period,
            ],
        )

        allowed, remaining, reset = result

        return (
            bool(int(allowed)),
            int(remaining),
            int(reset),
        )

    def cleanup(self, key: str | None = None):
        """Remove an expired Redis counter.

        Redis EXPIRE handles normal expiration automatically.
        """

        if key is None:
            return

        reset = self.client.hget(key, "reset")

        if reset is None:
            return

        now = int(time())

        if int(reset) <= now:
            self.client.delete(key)
