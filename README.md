# Flask-Limit

[![Build](https://github.com/tabotkevin/flask_limit/actions/workflows/build.yaml/badge.svg)](https://github.com/tabotkevin/flask_limit/actions/workflows/build.yaml)
[![Documentation](https://readthedocs.org/projects/flask-limit/badge/?version=latest)](https://flask-limit.readthedocs.io/en/latest/?badge=latest)
[![image](https://img.shields.io/pypi/v/flask-limit.svg)](https://pypi.org/project/flask_limit/)
[![image](https://img.shields.io/pypi/pyversions/flask-limit.svg)](https://pypi.org/project/flask-limit/)
[![image](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![image](https://img.shields.io/github/contributors/tabotkevin/flask_limit.svg)](https://github.com/tabotkevin/flask_limit/graphs/contributors)

A lightweight, high-performance rate-limiting extension for Flask applications. **Flask-Limit** protects your API endpoints from brute-force attacks and abuse by restricting how many requests a client can make within a given time window.

---

## Features

- ⚡ **Flexible Backends**: In-memory store for development; Redis for distributed production deployments.
- ⚙️ **Route-Level & Global Controls**: Set global limits or override rules on individual routes.
- 🔌 **Auto-Registering Extensibility**: Add custom storage backends (MongoDB, DynamoDB, Postgres) simply by subclassing `Limiter`.
- 🛠️ **Customizable Responses**: Customize rate-limit exceeded responses globally or per endpoint.
- 🏷️ **Standard HTTP Headers**: Automatically injects `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.

---

## Installation

Install the base package using `pip`:

```bash
pip install flask-limit

```

### Optional Extras

To use third-party storage backends, install the corresponding extra:

```bash
# Redis Backend
pip install "flask-limit[redis]"

# All Backends
pip install "flask-limit[all]"

```

---

## Configuration

Configure default behaviors using standard Flask `app.config` keys:

| Config Key             | Default Value                | Description                                                   |
| ---------------------- | ---------------------------- | ------------------------------------------------------------- |
| `RATELIMIT_LIMIT`      | `100`                        | Default maximum requests allowed per window.                  |
| `RATELIMIT_PERIOD`     | `60`                         | Default window duration in seconds.                           |
| `RATELIMIT_KEY_PREFIX` | `"ratelimit"`                | Prefix prepended to backend tracking keys.                    |
| `RATELIMIT_REDIS_URL`  | `"redis://localhost:6379/0"` | Redis connection URL when using the `redis` backend.          |
| `RATELIMIT_RESPONSE`   | `None`                       | Application-level fallback for rate limit exceeded responses. |

---

## Quickstart

### 1. In-Memory Backend (Single Process)

Ideal for local testing and single-worker setups:

```python
from flask import Flask, jsonify
from flask_limit import RateLimiter

app = Flask(__name__)
app.config["RATELIMIT_LIMIT"] = 50
app.config["RATELIMIT_PERIOD"] = 60

# Initialize with default memory backend
limiter = RateLimiter(app, limiter="memory")

# Uses application defaults (50 requests / 60s)
@app.route("/api/users")
@limiter.rate_limit
def get_users():
    return jsonify({"users": []})

# Route-specific override (5 requests / 10s)
@app.route("/api/login", methods=["POST"])
@limiter.rate_limit(limit=5, period=10)
def login():
    return jsonify({"status": "authenticated"})

```

---

### 2. Redis Backend (Production / Multi-Worker)

Required for multi-worker environments (Gunicorn, uWSGI) or distributed servers:

```python
from flask import Flask, jsonify
from flask_limit import RateLimiter

app = Flask(__name__)
app.config["RATELIMIT_REDIS_URL"] = "redis://localhost:6379/0"

# Initialize with Redis backend
limiter = RateLimiter(app, limiter="redis")

@app.route("/api/data")
@limiter.rate_limit(limit=100, period=60)
def get_data():
    return jsonify({"data": "ok"})

```

---

## Customizing Exceeded Limit Responses

When a client hits a rate limit, Flask-Limit returns a `429 Too Many Requests` status code. You can customize the response at the application or route level.

### Application-Wide Response

Assign a function or response tuple to `RATELIMIT_RESPONSE` in `app.config`:

```python
from flask import jsonify
from flask_limit.types import RateLimitInfo

def custom_limit_exceeded(info: RateLimitInfo):
    return jsonify({
        "error": "rate_limit_exceeded",
        "retry_after_seconds": info.reset,
        "max_allowed": info.limit
    }), 429

app.config["RATELIMIT_RESPONSE"] = custom_limit_exceeded

```

### Route-Level Response Override

Pass a callable or tuple directly to the `@limiter.rate_limit` decorator:

```python
@app.route("/api/strict")
@limiter.rate_limit(
    limit=2,
    period=60,
    response=("Custom 429: Too many requests on this endpoint.", 429)
)
def strict_route():
    return jsonify({"status": "ok"})

```

---

## Custom Backends

Creating a custom storage backend is seamless. Simply inherit from `Limiter` and define a `name` in the class header—`Flask-Limit` will register it automatically!

```python
from flask_limit.limiters import Limiter

class MemcachedRateLimit(Limiter, name="memcached"):

    @classmethod
    def from_app(cls, app):
        # Build your backend instance using app config
        return cls(server=app.config["MEMCACHED_SERVER"])

    def is_allowed(self, key: str, limit: int, period: int):
        # Return tuple: (allowed: bool, remaining: int, reset: int)
        return True, limit - 1, period

    def cleanup(self, key=None):
        pass

# Use your new custom backend immediately!
limiter = RateLimiter(app, limiter="memcached")

```

---

## Documentation

For full API references, architecture guides, and Sphinx docs, check out the [Documentation](https://flask-limit.readthedocs.io/en/latest) in the repository.

---

## License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).
