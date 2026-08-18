import functools
import logging

from flask import current_app, g, jsonify, request

from .config import DEFAULT_CONFIG, EXTENSION_KEY
from .limiters import BACKEND_REGISTRY, LimiterException
from .types import RateLimitInfo

logger = logging.getLogger(__name__)


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

        backend_cls = BACKEND_REGISTRY.get(self.limiter)

        if backend_cls is None:
            available = ", ".join(BACKEND_REGISTRY.keys())
            raise LimiterException(
                f"Unknown backend '{self.limiter}'. Available: {available}"
            )

        return backend_cls.from_app(app)

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

    @staticmethod
    def _default_rate_limit_response(
        info: RateLimitInfo,
    ):
        response = jsonify(
            {
                "status": 429,
                "error": "too many requests",
                "message": ("You have exceeded your request rate"),
            }
        )

        response.status_code = 429

        return response

    def _rate_limit_response(
        self,
        info: RateLimitInfo,
        response=None,
    ):

        if response is None:
            response = current_app.config.get("RATELIMIT_RESPONSE")

        if response is None:
            return self._default_rate_limit_response(info)

        if callable(response):
            return response(info)

        return response

    def rate_limit(self, f=None, limit=None, period=None, response=None):
        """Limit a route to a number(limit) of requests per period.

        Args:
            limit:
                Maximum number of requests allowed.

            period:
                Rate-limit window in seconds.

            response:
                Custom response returned when the rate limit is
                exceeded.

                The value can be:

                - A callable accepting a RateLimitInfo object.
                - A Flask response.
                - A Flask response tuple.

                If ``None`` is supplied, the application-level
                ``RATELIMIT_RESPONSE`` configuration is used.

                If neither is configured, Flask-Limit's default
                429 response is returned.

        Examples:

            @limiter.rate_limit
            def endpoint():
                ...

            @limiter.rate_limit(limit=100, period=60)
            def endpoint():
                ...

            @limiter.rate_limit(
                limit=100,
                period=60,
                response=custom_response,
            )
            def endpoint():
                ...
        """

        if f is None:
            return functools.partial(
                self.rate_limit,
                limit=limit,
                period=period,
                response=response,
            )

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            configured_limit = current_app.config["RATELIMIT_LIMIT"]
            configured_period = current_app.config["RATELIMIT_PERIOD"]

            actual_limit = configured_limit if limit is None else limit

            actual_period = configured_period if period is None else period

            self._validate_limit(actual_limit, actual_period)

            backend = self._get_backend()

            key = self._make_key(f)

            allowed, remaining, reset = backend.is_allowed(
                key,
                actual_limit,
                actual_period,
            )

            rate_limit_info = RateLimitInfo(
                limit=actual_limit,
                remaining=remaining,
                reset=reset,
                period=actual_period,
                key=key,
            )

            g.rate_limit_headers = {
                "X-RateLimit-Limit": str(actual_limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset),
            }

            if not allowed:
                return self._rate_limit_response(rate_limit_info, response)

            return f(*args, **kwargs)

        return wrapped
