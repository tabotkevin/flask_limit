import os

import pytest
import redis


@pytest.fixture
def redis_client():
    url = os.getenv(
        "FLASK_LIMIT_REDIS_URL",
        "redis://localhost:6379/15",
    )

    client = redis.Redis.from_url(
        url,
        decode_responses=False,
    )

    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        pytest.skip("Redis is not available.")

    yield client

    client.flushdb()
    client.close()
