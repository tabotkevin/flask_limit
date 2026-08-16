import functools
import logging

from flask import current_app, g, jsonify, request
from flask_redis import FlaskRedis

from .limiters import LimiterException, MemRateLimiter, RedisRateLimiter

logger = logging.getLogger(__name__)


# RATELIMIT_LIMIT is the number of allowed requests
# RATELIMIT_PERIOD is the period in seconds for the number of allowed requests
DEFAULT_CONFIG = {
    "RATELIMIT_LIMIT": 10,
    "RATELIMIT_PERIOD": 20,
}


class RateLimiter:

    def __init__(self, app=None, limiter="memory"):
        if limiter not in ("memory", "redis"):
            raise LimiterException("Limiter value must be 'memory' or 'redis'.")

        self.limiter = limiter
        self._limiter = None
        self._redis = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):

        app.config.setdefault(
            "RATELIMIT_LIMIT",
            DEFAULT_CONFIG["RATELIMIT_LIMIT"],
        )

        app.config.setdefault(
            "RATELIMIT_PERIOD",
            DEFAULT_CONFIG["RATELIMIT_PERIOD"],
        )

        if self.limiter == "redis":
            app.config.setdefault(
                "REDIS_URL",
                "redis://localhost:6379/0",
            )

            self._redis = FlaskRedis(app)
            self._limiter = RedisRateLimiter(self._redis)

        else:
            self._limiter = MemRateLimiter()

        app.extensions["rate_limiter"] = self

    def rate_limit(self, f=None, limit=None, period=None):
        """Limit a route to a number(limit) of requests per period.

        Args:
            limit: Maximum number of requests allowed.
            period: Time window in seconds.
        """

        if f is None:
            return functools.partial(
                self.rate_limit,
                limit=limit,
                period=period,
            )

        limit = limit if limit is not None else current_app.config["RATELIMIT_LIMIT"]

        period = (
            period if period is not None else current_app.config["RATELIMIT_PERIOD"]
        )

        if limit <= 0:
            raise LimiterException("Rate limit must be greater than zero.")

        if period <= 0:
            raise LimiterException("Rate limit period must be greater than zero.")

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            key = "{0}/{1}".format(f.__name__, request.remote_addr)

            allowed, remaining, reset = self._limiter.is_allowed(
                key,
                limit,
                period,
            )

            g.rate_limit_headers = {
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Reset": str(reset),
            }

            if not allowed:
                response = jsonify(
                    {
                        "status": 429,
                        "error": "too many requests",
                        "message": ("You have exceeded your request rate"),
                    }
                )

                response.status_code = 429

                return response

            # else we let the request through
            return f(*args, **kwargs)

        return wrapped
