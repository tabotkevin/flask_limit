import logging
import functools
from time import time
from flask import current_app, request, g, jsonify

logger = logging.getLogger()

_limiter = None

default_config = {
    'RATELIMITE_LIMIT': 10,
    'RATELIMIT_PERIOD': 20
}

class MemRateLimit(object):
    """Rate limiter that uses a Python dictionary as storage."""
    def __init__(self):
        self.counters = {}

    def is_allowed(self, key, limit, period):
        """Check if the client's request should be allowed, based on the
        hit counter. Returns a 3-element tuple with a True/False result,
        the number of remaining hits in the period, and the time the
        counter resets for the next period."""
        now = int(time())
        begin_period = now // period * period
        end_period = begin_period + period

        self.cleanup(now)
        if key in self.counters:
            self.counters[key]['hits'] += 1
        else:
            self.counters[key] = {'hits': 1, 'reset': end_period}
        allow = True
        remaining = limit - self.counters[key]['hits']
        if remaining < 0:
            remaining = 0
            allow = False
        return allow, remaining, self.counters[key]['reset']

    def cleanup(self, now):
        """Eliminate expired keys."""
        for key, value in list(self.counters.items()):
            if value['reset'] < now:
                del self.counters[key]


class RateLimiter(object):

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if not (
            app.config.get('RATELIMITE_LIMIT')
            and app.config.get('RATELIMIT_PERIOD')
        ):
            logging.warn('Set both RATELIMITE_LIMIT and RATELIMIT_PERIOD in configuration. '
                         'Default value are being used.')
            for key, value in default_config.items():
                app.config.setdefault(key, value)
        app.app_context().push()

    def rate_limit(self, f=None, limit=None, period=None):
        """Limits the rate at which clients can send requests to 'limit' requests
        per 'period' seconds. Once a client goes over the limit all requests are
        answered with a status code 429 Too Many Requests for the remaining of
        that period."""
        if f is None:
            return functools.partial(self.rate_limit, limit=limit, period=period)
        limit = limit if limit else current_app.config['RATELIMITE_LIMIT']
        period = period if period else current_app.config['RATELIMIT_PERIOD']

        functools.wraps(f)
        def wrapped(*args, **kwargs):
            # initialize the rate limiter the first time here
            global _limiter
            if _limiter is None:
                _limiter = MemRateLimit()

            # generate a unique key to represent the decorated function and
            # the IP address of the client. Rate limiting counters are
            # maintained on each unique key.
            key = '{0}/{1}'.format(f.__name__, request.remote_addr)
            allowed, remaining, reset = _limiter.is_allowed(key, limit, period)

            # set the rate limit headers in g, so that they are picked up
            # by the after_request handler and attached to the response
            g.headers = {
                'X-RateLimit-Remaining': str(remaining),
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Reset': str(reset)
            }

            # if the client went over the limit respond with a 429 status
            # code, else invoke the wrapped function
            if not allowed:
                response = jsonify(
                    {'status': 429, 'error': 'too many requests',
                        'message': 'You have exceeded your request rate'})
                response.status_code = 429
                return response

            # else we let the request through
            return f(*args, **kwargs)
        return wrapped
