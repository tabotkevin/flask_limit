import time

import pytest

from flask_limit.limiters import MemRateLimiter


class TestMemRateLimit:
    @pytest.fixture
    def limiter(self):
        return MemRateLimiter()

    def test_first_request_is_allowed(self, limiter):
        allowed, remaining, reset = limiter.is_allowed(
            "test-key",
            limit=10,
            period=60,
        )

        assert allowed is True
        assert remaining == 9
        assert reset > int(time.time())

    def test_requests_are_counted(self, limiter):
        result = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert result[0] is True
        assert result[1] == 2

        result = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert result[0] is True
        assert result[1] == 1

        result = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert result[0] is True
        assert result[1] == 0

    def test_request_over_limit_is_rejected(self, limiter):
        for _ in range(3):
            allowed, _, _ = limiter.is_allowed(
                "test-key",
                limit=3,
                period=60,
            )

            assert allowed is True

        allowed, remaining, reset = limiter.is_allowed(
            "test-key",
            limit=3,
            period=60,
        )

        assert allowed is False
        assert remaining == 0
        assert reset > int(time.time())

    def test_requests_over_limit_remain_rejected(self, limiter):
        for _ in range(5):
            allowed, remaining, _ = limiter.is_allowed(
                "test-key",
                limit=2,
                period=60,
            )

        assert allowed is False
        assert remaining == 0

        allowed, remaining, _ = limiter.is_allowed(
            "test-key",
            limit=2,
            period=60,
        )

        assert allowed is False
        assert remaining == 0

    def test_different_keys_have_independent_counters(self, limiter):
        allowed, remaining, _ = limiter.is_allowed(
            "key-1",
            limit=2,
            period=60,
        )

        assert allowed is True
        assert remaining == 1

        allowed, remaining, _ = limiter.is_allowed(
            "key-1",
            limit=2,
            period=60,
        )

        assert allowed is True
        assert remaining == 0

        allowed, remaining, _ = limiter.is_allowed(
            "key-2",
            limit=2,
            period=60,
        )

        assert allowed is True
        assert remaining == 1

    def test_reset_timestamp_is_shared_by_requests_in_same_window(
        self,
        limiter,
    ):
        _, _, reset1 = limiter.is_allowed(
            "test-key",
            limit=10,
            period=60,
        )

        _, _, reset2 = limiter.is_allowed(
            "test-key",
            limit=10,
            period=60,
        )

        assert reset1 == reset2

    def test_expired_counter_starts_new_window(self, limiter, monkeypatch):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.memory.time",
            lambda: current_time,
        )

        allowed, remaining, reset1 = limiter.is_allowed(
            "test-key",
            limit=2,
            period=10,
        )

        assert allowed is True
        assert remaining == 1
        assert reset1 == 1010

        allowed, remaining, reset2 = limiter.is_allowed(
            "test-key",
            limit=2,
            period=10,
        )

        assert allowed is True
        assert remaining == 0
        assert reset2 == 1010

        # Move into the next window.
        current_time = 1_010

        allowed, remaining, reset3 = limiter.is_allowed(
            "test-key",
            limit=2,
            period=10,
        )

        assert allowed is True
        assert remaining == 1
        assert reset3 == 1020

    def test_cleanup_removes_expired_key(self, limiter, monkeypatch):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.memory.time",
            lambda: current_time,
        )

        limiter.is_allowed(
            "test-key",
            limit=10,
            period=10,
        )

        assert "test-key" in limiter.counters

        current_time = 1_010

        limiter.cleanup("test-key")

        assert "test-key" not in limiter.counters

    def test_cleanup_does_not_remove_active_key(
        self,
        limiter,
        monkeypatch,
    ):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.memory.time",
            lambda: current_time,
        )

        limiter.is_allowed(
            "test-key",
            limit=10,
            period=10,
        )

        current_time = 1_005

        limiter.cleanup("test-key")

        assert "test-key" in limiter.counters

    def test_cleanup_without_key_removes_all_expired_keys(
        self,
        limiter,
        monkeypatch,
    ):
        current_time = 1_000

        monkeypatch.setattr(
            "flask_limit.limiters.memory.time",
            lambda: current_time,
        )

        limiter.is_allowed(
            "expired-key",
            limit=10,
            period=10,
        )

        limiter.is_allowed(
            "active-key",
            limit=10,
            period=20,
        )

        current_time = 1_010

        limiter.cleanup()

        assert "expired-key" not in limiter.counters
        assert "active-key" in limiter.counters

    def test_cleanup_nonexistent_key_does_nothing(self, limiter):
        limiter.cleanup("does-not-exist")

        assert limiter.counters == {}

    def test_counter_is_thread_safe(self, limiter):
        from concurrent.futures import ThreadPoolExecutor

        def make_request():
            return limiter.is_allowed(
                "test-key",
                limit=1000,
                period=60,
            )

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(
                executor.map(
                    lambda _: make_request(),
                    range(100),
                )
            )

        assert all(result[0] is True for result in results)

        assert limiter.counters["test-key"]["hits"] == 100
