import unittest
import base64
from flask import Flask
from flask_limiter import RateLimiter


class RateLimiterTestCase(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config['RATELIMITE_LIMIT'] = 10
        app.config['RATELIMIT_PERIOD'] = 30

        limiter = RateLimiter(app)

        @app.before_request
        @limiter.rate_limit
        def before_request():
            pass

        @app.after_request
        def after_request(rv):
            headers = getattr(g, 'headers', {})
            rv.headers.extend(headers)
            return rv


        @app.route('/greet/<name>')
        def greet(name):
            return f'Hello {name}!'


        @app.route('/get-auth-token')
        @limiter.rate_limit(limit=1, period=600)  # one call per 10 minute period
        def get_auth_token():
            return {'token': '<auth-token>'}

        self.app = app
        self.client = app.test_client()

    def test_before_request(self):
        pass
        

    def test_more_than_route(self):
        pass
