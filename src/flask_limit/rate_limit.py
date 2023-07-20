import logging
import functools

from flask import current_app, request, g, jsonify
from flask_redis import FlaskRedis

from .limiters import MemRateLimit, RedisRateLimit, LimiterException

logger = logging.getLogger()

_limiter = None

# RATELIMIT_LIMIT is the number of allowed requests
# RATELIMIT_PERIOD is the period in seconds for the number of allowed requests
DEFAULT_CONFIG = {"RATELIMIT_LIMIT": 10, "RATELIMIT_PERIOD": 20}


class RateLimiter(object):
    def __init__(self, app=None, limiter="memory"):
        if limiter not in ["memory", "redis"]:
            raise LimiterException("Limiter value must be 'memory' or 'redis'.")
        self.limiter = limiter
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if self.limiter == "redis" and not app.config.get("REDIS_URL"):
            logger.warning(
                "Set REDIS_URL in configuration. Default value is being used."
            )
            app.config.update(REDIS_URL="redis://localhost:6379/0")
        if not (
            app.config.get("RATELIMIT_LIMIT") and app.config.get("RATELIMIT_PERIOD")
        ):
            logger.warning(
                "Set both RATELIMIT_LIMIT and RATELIMIT_PERIOD in configuration. "
                "Default values are being used."
            )
            app.config.update(**DEFAULT_CONFIG)
        app.app_context().push()

    def rate_limit(self, f=None, limit=None, period=None):
        """Limits the rate at which clients can send requests to 'limit' requests
        per 'period' seconds. Once a client goes over the limit all requests are
        answered with a status code 429 Too Many Requests for the remaining of
        that period."""
        if f is None:
            return functools.partial(self.rate_limit, limit=limit, period=period)
        limit = limit if limit else current_app.config["RATELIMIT_LIMIT"]
        period = period if period else current_app.config["RATELIMIT_PERIOD"]

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # initialize the rate limiter the first time here
            global _limiter
            if _limiter is None:
                if self.limiter == "redis":
                    reids_client = FlaskRedis(current_app)
                    _limiter = RedisRateLimit(reids_client)
                else:
                    _limiter = MemRateLimit()

            # generate a unique key to represent the decorated function and
            # the IP address of the client. Rate limiting counters are
            # maintained on each unique key.
            key = "{0}/{1}".format(f.__name__, request.remote_addr)
            allowed, remaining, reset = _limiter.is_allowed(key, limit, period)

            # set the rate limit headers in g, so that they are picked up
            # by the after_request handler and attached to the response
            g.headers = {
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Reset": str(reset),
            }

            # if the client went over the limit respond with a 429 status
            # code, else invoke the wrapped function
            if not allowed:
                response = jsonify(
                    {
                        "status": 429,
                        "error": "too many requests",
                        "message": "You have exceeded your request rate",
                    }
                )
                response.status_code = 429
                return response

            # else we let the request through
            return f(*args, **kwargs)

        return wrapped
