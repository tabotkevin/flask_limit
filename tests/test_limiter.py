import pytest

from flask_limit.limiters import (
    Limiter,
    LimiterException,
)


class TestLimiter:
    def test_cannot_instantiate_abstract_limiter(self):
        with pytest.raises(TypeError):
            Limiter()

    def test_limiter_exception_is_exception(self):
        assert issubclass(LimiterException, Exception)
