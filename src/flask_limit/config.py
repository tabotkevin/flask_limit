EXTENSION_KEY = "flask_limit"

DEFAULT_CONFIG = {
    "RATELIMIT_LIMIT": 10,
    "RATELIMIT_PERIOD": 20,
    "RATELIMIT_KEY_PREFIX": "flask-limit",
    "RATELIMIT_REDIS_URL": "redis://localhost:6379/0",
    "RATELIMIT_RESPONSE": None,
}
