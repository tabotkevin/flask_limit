import functools
import logging

from flask import current_app, g, jsonify, request

from .limiters import LimiterException, MemRateLimiter, RedisRateLimiter

logger = logging.getLogger(__name__)

EXTENSION_KEY = "flask_limit"

DEFAULT_CONFIG = {
    "RATELIMIT_LIMIT": 10,
    "RATELIMIT_PERIOD": 20,
    "RATELIMIT_KEY_PREFIX": "flask-limit",
    "RATELIMIT_REDIS_URL": "redis://localhost:6379/0",
}


class RateLimiter:

    def __init__(self, app=None, limiter="memory"):
        if limiter not in ("memory", "redis"):
            raise LimiterException("Limiter value must be 'memory' or 'redis'.")

        self.limiter = limiter

        if app is not None:
            self.init_app(app)

    def init_app(self, app):

        self._configure(app)

        backend = self._create_backend(app)

        app.extensions[EXTENSION_KEY] = {
            "extension": self,
            "backend": backend,
        }

        app.after_request(self._add_rate_limit_headers)

    def _configure(self, app):

        for key, value in DEFAULT_CONFIG.items():
            app.config.setdefault(key, value)

        limit = app.config["RATELIMIT_LIMIT"]
        period = app.config["RATELIMIT_PERIOD"]

        if not isinstance(limit, int):
            raise LimiterException("RATELIMIT_LIMIT must be an integer.")

        if limit <= 0:
            raise LimiterException("RATELIMIT_LIMIT must be greater than zero.")

        if not isinstance(period, int):
            raise LimiterException("RATELIMIT_PERIOD must be an integer.")

        if period <= 0:
            raise LimiterException("RATELIMIT_PERIOD must be greater than zero.")

    def _get_backend(self):
        extension = current_app.extensions.get(EXTENSION_KEY)

        if extension is None:
            raise LimiterException(
                "flask-limit has not been initialized for this application."
            )

        return extension["backend"]

    def _create_backend(self, app):
        if self.limiter == "memory":
            return MemRateLimiter()

        return self._create_redis_backend(app)

    @staticmethod
    def _create_redis_backend(app):
        try:
            import redis
        except ImportError as exc:
            raise LimiterException(
                "Redis support requires the 'redis' package. "
                "Install it with: pip install redis"
            ) from exc

        redis_url = app.config["RATELIMIT_REDIS_URL"]

        client = redis.Redis.from_url(
            redis_url,
            decode_responses=False,
        )

        return RedisRateLimiter(client)

    @staticmethod
    def _validate_limit(limit, period):

        if not isinstance(limit, int):
            raise LimiterException("Rate limit must be an integer.")

        if limit <= 0:
            raise LimiterException("Rate limit must be greater than zero.")

        if not isinstance(period, int):
            raise LimiterException("Rate limit period must be an integer.")

        if period <= 0:
            raise LimiterException("Rate limit period must be greater than zero.")

    @staticmethod
    def _add_rate_limit_headers(response):

        headers = getattr(g, "rate_limit_headers", None)

        if headers:
            for name, value in headers.items():
                response.headers[name] = value

        return response

    @staticmethod
    def _make_key(f):

        endpoint = request.endpoint or f.__name__
        client_ip = request.remote_addr or "unknown"
        prefix = current_app.config["RATELIMIT_KEY_PREFIX"]

        return f"{prefix}:{endpoint}:{client_ip}"

    def rate_limit(self, f=None, limit=None, period=None):
        """Limit a route to a number(limit) of requests per period.

        Args:
            limit: Maximum number of requests allowed.
            period: Time window in seconds.

        Usage:

            @limiter.rate_limit
            def endpoint():
                ...

        Or:

            @limiter.rate_limit(limit=100, period=60)
            def endpoint():
                ...
        """

        if f is None:
            return functools.partial(
                self.rate_limit,
                limit=limit,
                period=period,
            )

        configured_limit = current_app.config["RATELIMIT_LIMIT"]
        configured_period = current_app.config["RATELIMIT_PERIOD"]

        limit = configured_limit if limit is None else limit

        period = configured_period if period is None else period

        self._validate_limit(limit, period)

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            backend = self._get_backend()

            key = self._make_key(f)

            allowed, remaining, reset = backend.is_allowed(
                key,
                limit,
                period,
            )

            g.rate_limit_headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
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

            return f(*args, **kwargs)

        return wrapped
