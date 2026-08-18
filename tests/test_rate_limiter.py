from unittest.mock import MagicMock

import pytest
from flask import Flask, jsonify

from flask_limit import RateLimiter
from flask_limit.config import EXTENSION_KEY
from flask_limit.limiters import BACKEND_REGISTRY, LimiterException
from flask_limit.types import RateLimitInfo


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.is_allowed.return_value = (True, 9, 100)
    return backend


@pytest.fixture
def mock_backend_cls(mock_backend):
    cls = MagicMock()
    cls.from_app.return_value = mock_backend
    return cls


@pytest.fixture(autouse=True)
def register_mock_backends(monkeypatch, mock_backend_cls):
    monkeypatch.setitem(BACKEND_REGISTRY, "memory", mock_backend_cls)
    monkeypatch.setitem(BACKEND_REGISTRY, "redis", mock_backend_cls)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["RATELIMIT_KEY_PREFIX"] = "test"
    app.config["RATELIMIT_LIMIT"] = 10
    app.config["RATELIMIT_PERIOD"] = 60
    return app


@pytest.fixture
def limiter(app):
    return RateLimiter(app, limiter="memory")


@pytest.fixture
def client(app):
    return app.test_client()


def test_init_valid_limiters(app):
    limiter_mem = RateLimiter(limiter="memory")
    limiter_redis = RateLimiter(limiter="redis")
    assert limiter_mem.limiter == "memory"
    assert limiter_redis.limiter == "redis"


def test_init_invalid_limiter_raises_exception():
    with pytest.raises(
        LimiterException, match="Limiter value must be 'memory' or 'redis'"
    ):
        RateLimiter(limiter="invalid_backend")


def test_init_app_registers_extension(app):
    limiter = RateLimiter()
    limiter.init_app(app)

    assert EXTENSION_KEY in app.extensions
    assert app.extensions[EXTENSION_KEY]["extension"] == limiter
    assert "backend" in app.extensions[EXTENSION_KEY]


@pytest.mark.parametrize(
    "config_override, error_msg",
    [
        ({"RATELIMIT_LIMIT": "not-an-int"}, "RATELIMIT_LIMIT must be an integer"),
        ({"RATELIMIT_LIMIT": 0}, "RATELIMIT_LIMIT must be greater than zero"),
        ({"RATELIMIT_LIMIT": -5}, "RATELIMIT_LIMIT must be greater than zero"),
        ({"RATELIMIT_PERIOD": "not-an-int"}, "RATELIMIT_PERIOD must be an integer"),
        ({"RATELIMIT_PERIOD": 0}, "RATELIMIT_PERIOD must be greater than zero"),
        ({"RATELIMIT_PERIOD": -10}, "RATELIMIT_PERIOD must be greater than zero"),
    ],
)
def test_invalid_configuration_raises_exception(app, config_override, error_msg):
    app.config.update(config_override)
    limiter = RateLimiter()

    with pytest.raises(LimiterException, match=error_msg):
        limiter.init_app(app)


def test_create_backend_calls_from_app(app, mock_backend_cls):
    limiter = RateLimiter(limiter="memory")
    backend = limiter._create_backend(app)

    mock_backend_cls.from_app.assert_called_once_with(app)
    assert backend == mock_backend_cls.from_app.return_value


def test_get_backend_without_init_app_raises_exception(app):
    limiter = RateLimiter()
    with app.app_context():
        with pytest.raises(
            LimiterException, match="flask-limit has not been initialized"
        ):
            limiter._get_backend()


def test_rate_limit_allows_request_and_sets_headers(app, limiter, client, mock_backend):
    mock_backend.is_allowed.return_value = (True, 9, 100)

    @app.route("/test")
    @limiter.rate_limit
    def test_route():
        return "OK"

    response = client.get("/test")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "OK"
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "9"
    assert response.headers["X-RateLimit-Reset"] == "100"


def test_rate_limit_blocks_request_and_returns_default_429(
    app, limiter, client, mock_backend
):
    mock_backend.is_allowed.return_value = (False, 0, 120)

    @app.route("/blocked")
    @limiter.rate_limit
    def blocked_route():
        return "OK"

    response = client.get("/blocked")

    assert response.status_code == 429
    json_data = response.get_json()
    assert json_data["status"] == 429
    assert json_data["error"] == "too many requests"
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert response.headers["X-RateLimit-Reset"] == "120"


def test_rate_limit_custom_decorator_parameters(app, limiter, client, mock_backend):
    @app.route("/custom")
    @limiter.rate_limit(limit=5, period=30)
    def custom_route():
        return "OK"

    client.get("/custom")

    args, _ = mock_backend.is_allowed.call_args
    assert args[1] == 5
    assert args[2] == 30


@pytest.mark.parametrize(
    "limit, period, error_msg",
    [
        ("invalid", 60, "Rate limit must be an integer"),
        (0, 60, "Rate limit must be greater than zero"),
        (10, "invalid", "Rate limit period must be an integer"),
        (10, 0, "Rate limit period must be greater than zero"),
    ],
)
def test_rate_limit_decorator_invalid_args_raises_exception(
    app, limiter, client, limit, period, error_msg
):
    @app.route("/invalid-args")
    @limiter.rate_limit(limit=limit, period=period)
    def invalid_route():
        return "OK"

    with pytest.raises(LimiterException, match=error_msg):
        client.get("/invalid-args")


def test_rate_limit_custom_callable_response(app, limiter, client, mock_backend):
    mock_backend.is_allowed.return_value = (False, 0, 60)

    def custom_response_handler(info: RateLimitInfo):
        return jsonify({"custom_error": f"Limit of {info.limit} exceeded"}), 429

    @app.route("/custom-resp")
    @limiter.rate_limit(response=custom_response_handler)
    def custom_resp_route():
        return "OK"

    response = client.get("/custom-resp")

    assert response.status_code == 429
    assert response.get_json() == {"custom_error": "Limit of 10 exceeded"}


def test_rate_limit_custom_response_from_app_config(app, limiter, client, mock_backend):
    mock_backend.is_allowed.return_value = (False, 0, 60)
    app.config["RATELIMIT_RESPONSE"] = ("Configured limit exceeded", 429)

    @app.route("/config-resp")
    @limiter.rate_limit
    def config_resp_route():
        return "OK"

    response = client.get("/config-resp")

    assert response.status_code == 429
    assert response.get_data(as_text=True) == "Configured limit exceeded"


def test_make_key(app, limiter):
    def dummy_endpoint():
        pass

    with app.test_request_context(
        "/test-path", environ_base={"REMOTE_ADDR": "192.168.1.1"}
    ):
        key = limiter._make_key(dummy_endpoint)
        assert key == "test:dummy_endpoint:192.168.1.1"


def test_make_key_fallback_remote_addr(app, limiter):
    def dummy_endpoint():
        pass

    with app.test_request_context("/test-path"):
        key = limiter._make_key(dummy_endpoint)
        assert key == "test:dummy_endpoint:unknown"
