===========
Flask-Limit
===========

Flask-Limit is a lightweight, high-performance rate limiting extension for Flask applications. 
It protects your API endpoints from brute-force attacks and abuse by restricting how many 
requests a client can make within a given time window.

It supports two storage backends:
* **Memory**: Thread-safe, process-local memory. Perfect for single-worker or development environments.
* **Redis**: Atomic, distributed rate limiting using Lua scripts. Essential for multi-worker production deployments.

Installation
============

Install and update using ``pip``:

.. code-block:: bash

    pip install flask-limit

Optional Extras
---------------

Built-in storage backends like Redis require optional third-party packages. You can install these extras directly alongside ``flask-limit``:

* **Redis backend:**

  .. code-block:: bash

      pip install "flask-limit[redis]"

* **All optional backends:**

  .. code-block:: bash

      pip install "flask-limit[all]"

Configuration
=============

Flask-Limit is configured via the standard Flask ``app.config`` dictionary. 

.. list-table:: 
   :widths: 30 15 55
   :header-rows: 1

   * - Configuration Key
     - Default
     - Description
   * - ``RATELIMIT_LIMIT``
     - ``10``
     - Default maximum number of allowed requests per window.
   * - ``RATELIMIT_PERIOD``
     - ``20``
     - Default rate limit window duration in seconds.
   * - ``RATELIMIT_KEY_PREFIX``
     - ``"flask-limit"``
     - String prefix attached to all storage keys to prevent collisions.
   * - ``RATELIMIT_REDIS_URL``
     - ``"redis://localhost:6379/0"``
     - Connection string used when the ``redis`` backend is active.
   * - ``RATELIMIT_RESPONSE``
     - ``None``
     - Global fallback for rate limit exceeded responses. Can be a callable.

Quickstart
==========

Memory Backend (Single-Process)
-------------------------------

The memory backend is enabled by default. It requires zero setup but does not share state across multiple workers (like Gunicorn or uWSGI).

.. code-block:: python

    from flask import Flask, jsonify
    from flask_limit import RateLimiter

    app = Flask(__name__)

    # Optional: override default limits
    app.config["RATELIMIT_LIMIT"] = 5
    app.config["RATELIMIT_PERIOD"] = 10  

    # Initialize with memory backend
    limiter = RateLimiter(app, limiter="memory")

    @app.route("/api/data")
    @limiter.rate_limit  # Use configured defaults
    def get_data():
        return jsonify({"data": "Hello World!"})

    @app.route("/api/strict")
    @limiter.rate_limit(limit=2, period=60) # Override route specifically
    def strict_data():
        return jsonify({"data": "Strictly limited."})

.. note::
   When using the memory backend in a long-running production environment, inactive counters will remain in memory. You should periodically run ``limiter._get_backend().cleanup()`` via a background task scheduler to prune expired keys and prevent memory bloat.

Redis Backend (Production)
--------------------------

For multi-worker or multi-server deployments, use the Redis backend. It automatically cleans up expired keys via Redis TTL and uses Lua scripts to guarantee thread safety and prevent race conditions.

.. code-block:: python

    from flask import Flask, jsonify
    from flask_limit import RateLimiter

    app = Flask(__name__)
    app.config["RATELIMIT_REDIS_URL"] = "redis://redis-server.local:6379/0"

    # Initialize with Redis backend
    limiter = RateLimiter(app, limiter="redis")

    @app.route("/")
    @limiter.rate_limit(limit=100, period=60)
    def index():
        return jsonify({"status": "ok"})


Customizing Responses
=====================

By default, Flask-Limit returns a standard ``429 Too Many Requests`` JSON response. You can customize this globally or per-route by providing a callable that takes a ``RateLimitInfo`` object.

Application-Level Custom Response
---------------------------------

Set `RATELIMIT_RESPONSE` in `app.config` using a callable or a response tuple:

.. code-block:: python

    from flask import jsonify

    def custom_429_handler(info):
        return jsonify({
            "error": "rate_limit_exceeded",
            "retry_after_seconds": info.reset,
            "max_allowed": info.limit,
        }), 429

    app.config["RATELIMIT_RESPONSE"] = custom_429_handler


Route-Level Custom Response
---------------------------

Pass a custom response directly to individual routes to override application defaults:


.. code-block:: python

    from flask import make_response
    from flask_limit import RateLimitInfo

    def custom_429(info: RateLimitInfo):
        response = make_response({
            "error": "Rate limit exceeded.",
            "try_again_in_seconds": info.reset - int(time())
        }, 429)
        return response

    # Apply to a specific route
    @app.route("/custom")
    @limiter.rate_limit(limit=5, period=10, response=custom_429)
    def custom_route():
        return "Success"

    app.route("/strict-endpoint")
    @limiter.rate_limit(
        limit=2, 
        period=60, 
        response=("Action limit reached. Try again later.", 429)  # response tuple
    )
    def strict_endpoint():
        return "Allowed"


Creating Custom Backends
========================

Backends automatically register themselves upon definition by inheriting from `Limiter`:

.. code-block:: python

    from flask_limit.limiters import Limiter

    class MongoRateLimit(Limiter, name="mongo"):

        def __init__(self, db_client):
            self.db = db_client

        @classmethod
        def from_app(cls, app):
            client = create_mongo_client(app.config["MONGO_URI"])
            return cls(client)

        def is_allowed(self, key: str, limit: int, period: int):
            # Check and increment counter logic
            # Returns tuple: (allowed: bool, remaining: int, reset_ttl: int)
            return True, limit - 1, period


After defining the class, initialize the extension using the assigned `name`:

.. code-block:: python

    limiter = RateLimiter(app, limiter="mongo")


API Reference
=============

.. currentmodule:: flask_limit

RateLimiter
-----------

.. class:: RateLimiter(app=None, limiter="memory")

    The core extension class.

    .. method:: init_app(app)

        Initialize the extension with the given Flask application context.

    .. method:: rate_limit(f=None, limit=None, period=None, response=None)

        Decorator to apply rate limiting to a Flask route.

        :param limit: Maximum number of requests allowed. Falls back to config.
        :param period: Rate-limit window in seconds. Falls back to config.
        :param response: Custom response returned when the rate limit is exceeded. Can be a Flask response, a tuple, or a callable accepting a ``RateLimitInfo`` object.

RateLimitInfo
-------------

.. class:: types.RateLimitInfo

    A dataclass passed to custom response handlers containing current limit data.

    .. attribute:: limit
        :type: int
        
        The maximum number of requests allowed in the period.

    .. attribute:: remaining
        :type: int
        
        The number of requests remaining in the current window.

    .. attribute:: reset
        :type: int
        
        A Unix timestamp representing when the current window expires.

    .. attribute:: period
        :type: int
        
        The duration of the window in seconds.

    .. attribute:: key
        :type: str
        
        The internal storage key generated for this user/endpoint combination.


Backends
--------

.. py:module:: flask_limit.limiters

Limiter
^^^^^^^

.. py:class:: Limiter

   Abstract base class for all rate limiter backends. Custom backends inherit from this class to automatically register with ``BACKEND_REGISTRY`` via ``__init_subclass__``.

   .. py:classmethod:: from_app(app)

      Abstract factory class method to build and configure a backend instance from a Flask application instance.

      :param app: Flask application instance.
      :type app: flask.Flask
      :return: An initialized backend instance.
      :rtype: Limiter
      :raises LimiterException: If required configuration is missing or invalid.

   .. py:method:: is_allowed(key, limit, period)

      Abstract method to evaluate if a request key is permitted within the rate limit window.

      :param str key: Unique request identifier (e.g., endpoint + IP address).
      :param int limit: Maximum allowed requests within the time window.
      :param int period: Rate limit window duration in seconds.
      :return: A tuple containing:
         * **allowed** (*bool*): ``True`` if request is allowed, ``False`` if rate limit exceeded.
         * **remaining** (*int*): Remaining request quota for the current window.
         * **reset** (*int*): Time in seconds until the current rate limit resets.
      :rtype: tuple[bool, int, int]

  .. py:method:: cleanup(key=None)

      Abstract method to purge expired entries or explicitly remove a specific rate limit record.

      :param str key: Optional request key to purge. If ``None``, performs general cleanup/purging of expired entries.
      :type key: str or None


MemRateLimiter
^^^^^^^^^^^^^^

.. py:class:: MemRateLimiter

   Bases: :py:class:`Limiter`

   In-memory rate limit backend. Stores request counts in local process memory. Automatically registered under the name ``"memory"``.

   .. note::
      In-memory storage is isolated to a single process. In multi-worker Gunicorn or uWSGI deployments, request counters are not shared across worker processes.

   .. py:classmethod:: from_app(app)

      Instantiates a memory backend instance. Requires no special configuration from ``app.config``.

      :param app: Flask application instance.
      :type app: flask.Flask
      :return: An instance of ``MemRateLimiter``.
      :rtype: MemRateLimiter

   .. py:method:: is_allowed(key, limit, period)

      Evaluates and increments the in-memory request counter for the given key.

      :param str key: Unique request key.
      :param int limit: Maximum allowed requests.
      :param int period: Window duration in seconds.
      :return: Tuple of ``(allowed, remaining, reset)``.
      :rtype: tuple[bool, int, int]

  .. py:method:: cleanup(key=None)

      Purges expired rate-limit tracking entries from memory, or explicitly removes a specific key.

      :param str key: Optional key to delete. If ``None``, iterates through stored records and removes all expired entries.
      :type key: str or None


RedisRateLimiter
^^^^^^^^^^^^^^^^

.. py:class:: RedisRateLimiter(client)

   Bases: :py:class:`Limiter`

   Distributed rate limit backend powered by Redis. Suitable for multi-worker and multi-server production environments. Automatically registered under the name ``"redis"``.

   :param client: Initialized Redis client instance.
   :type client: redis.Redis

   .. py:classmethod:: from_app(app)

      Constructs a ``RedisRateLimiter`` using the connection URL defined in ``app.config["RATELIMIT_REDIS_URL"]``.

      :param app: Flask application instance.
      :type app: flask.Flask
      :return: An instance of ``RedisRateLimiter``.
      :rtype: RedisRateLimiter
      :raises LimiterException: If the ``redis`` package is not installed or ``RATELIMIT_REDIS_URL`` is unconfigured or invalid.

   .. py:method:: is_allowed(key, limit, period)

      Executes atomic counter evaluation and TTL checks against the Redis database.

      :param str key: Unique request key.
      :param int limit: Maximum allowed requests.
      :param int period: Window duration in seconds.
      :return: Tuple of ``(allowed, remaining, reset)``.
      :rtype: tuple[bool, int, int]

  .. py:method:: cleanup(key=None)

      Deletes a specific key or set of keys in Redis.

      .. note::
         Redis automatically handles key expiration using TTLs set during ``is_allowed``. This method is primarily used for manual resets or administrative cache invalidation.

      :param str key: Optional key to explicitly delete from Redis. If ``None``, cleans up entries matching the configured key pattern.
      :type key: str or None
