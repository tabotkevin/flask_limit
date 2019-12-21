import unittest
from flask import Flask, g
import json
from flask_limit import RateLimiter


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
            return self.greeting

        @app.route('/get-auth-token')
        @limiter.rate_limit(limit=1, period=600)  # one call per 10 minute period
        def get_auth_token():
            return self.token

        self.app = app
        self.client = app.test_client()
        self.name = 'Tabot'
        self.greeting = f'Hello {self.name}!'
        self.error_message = {
            "error": "too many requests",
            "message": "You have exceeded your request rate",
            "status": 429
        }

    def test_rate_limit(self):
        limit = self.app.config['RATELIMITE_LIMIT']
        count = limit
        while count > 0:
            if count != 0:
                response = self.client.get(f'/greet/{self.name}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['X-RateLimit-Limit'], str(limit))
                self.assertEqual(response.headers['X-RateLimit-Remaining'], str(count-1))
                self.assertEqual(response.data.decode('utf-8'), self.greeting)
            else:
                self.assertEqual(response.status_code, 429)
                self.assertEqual(json.loads(response.data.decode('utf-8')), self.error_message)
            count -= 1
