import pytest

from flask_limit.limiters import RedisRateLimiter


@pytest.fixture
def limiter(redis_client):
    return RedisRateLimiter(redis_client)


class TestRedisRateLimit:
    def test_first_request_is_allowed(self, limiter):
        allowed, remaining, reset = limiter.is_allowed(
            "test-key",
            limit=10,
            period=60,
        )

        assert allowed is True
        assert remaining == 9
        assert reset > 0

    def test_requests_are_counted(self, limiter):
        allowed, remaining, _ = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert allowed is True
        assert remaining == 2

        allowed, remaining, _ = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert allowed is True
        assert remaining == 1

        allowed, remaining, _ = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert allowed is True
        assert remaining == 0

    def test_request_over_limit_is_rejected(self, limiter):
        for _ in range(3):
            allowed, _, _ = limiter.is_allowed(
                "test-key",
                limit=3,
                period=60,
            )

            assert allowed is True

        allowed, remaining, _ = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert allowed is False
        assert remaining == 0

    def test_requests_over_limit_remain_rejected(self, limiter):
        for _ in range(10):
            allowed, remaining, _ = limiter.is_allowed(
                "test-key",
                limit=2,
                period=60,
            )

        assert allowed is False
        assert remaining == 0

    def test_different_keys_have_independent_counters(
        self,
        limiter,
        redis_client,
    ):
        limiter.is_allowed(
            "key-1",
            limit=2,
            period=60,
        )

        limiter.is_allowed(
            "key-1",
            limit=2,
            period=60,
        )

        allowed, remaining, _ = limiter.is_allowed(
            "key-1",
            limit=2,
            period=60,
        )

        assert allowed is False
        assert remaining == 0

        allowed, remaining, _ = limiter.is_allowed(
            "key-2",
            limit=2,
            period=60,
        )

        assert allowed is True
        assert remaining == 1

    def test_redis_key_contains_hits_and_reset(
        self,
        limiter,
        redis_client,
    ):
        limiter.is_allowed(
            "test-key",
            limit=10,
            period=60,
        )

        assert (
            redis_client.hget(
                "test-key",
                "hits",
            )
            == b"1"
        )

        assert (
            redis_client.hget(
                "test-key",
                "reset",
            )
            is not None
        )

    def test_redis_key_has_expiration(
        self,
        limiter,
        redis_client,
    ):
        limiter.is_allowed(
            "test-key",
            limit=10,
            period=60,
        )

        ttl = redis_client.ttl("test-key")

        assert ttl > 0
        assert ttl <= 60

    def test_cleanup_removes_expired_key(
        self,
        limiter,
        redis_client,
        monkeypatch,
    ):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.redis.time",
            lambda: current_time,
        )

        limiter.is_allowed(
            "test-key",
            limit=10,
            period=10,
        )

        assert redis_client.exists("test-key")

        current_time = 1_010

        limiter.cleanup("test-key")

        assert not redis_client.exists("test-key")

    def test_cleanup_does_not_remove_active_key(
        self,
        limiter,
        redis_client,
        monkeypatch,
    ):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.redis.time",
            lambda: current_time,
        )

        limiter.is_allowed(
            "test-key",
            limit=10,
            period=10,
        )

        current_time = 1_005

        limiter.cleanup("test-key")

        assert redis_client.exists("test-key")

    def test_cleanup_nonexistent_key_does_nothing(
        self,
        limiter,
        redis_client,
    ):
        limiter.cleanup("does-not-exist")

        assert not redis_client.exists("does-not-exist")

    def test_counter_resets_after_window(
        self,
        limiter,
        redis_client,
        monkeypatch,
    ):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.redis.time",
            lambda: current_time,
        )

        allowed, remaining, reset = limiter.is_allowed(
            "test-key",
            limit=2,
            period=10,
        )

        assert allowed is True
        assert remaining == 1
        assert reset == 1010

        allowed, remaining, _ = limiter.is_allowed(
            "test-key",
            limit=2,
            period=10,
        )

        assert allowed is True
        assert remaining == 0

        current_time = 1_010

        allowed, remaining, reset = limiter.is_allowed(
            "test-key",
            limit=2,
            period=10,
        )

        assert allowed is True
        assert remaining == 1
        assert reset == 1020

        assert (
            redis_client.hget(
                "test-key",
                "hits",
            )
            == b"1"
        )

    def test_atomic_increment_under_concurrency(
        self,
        limiter,
    ):
        from concurrent.futures import ThreadPoolExecutor

        limit = 100

        def make_request():
            return limiter.is_allowed(
                "concurrent-key",
                limit=limit,
                period=60,
            )

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(
                executor.map(
                    lambda _: make_request(),
                    range(100),
                )
            )

        allowed_count = sum(result[0] for result in results)

        assert allowed_count == 100

        # The next request must be rejected.
        allowed, remaining, _ = limiter.is_allowed(
            "concurrent-key",
            limit=limit,
            period=60,
        )

        assert allowed is False
        assert remaining == 0
