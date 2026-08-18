from abc import ABC, abstractmethod


class LimiterException(Exception):
    pass


class Limiter(ABC):

    @abstractmethod
    def is_allowed(self, key: str, limit: int, period: int):
        """Check whether a request is allowed.

        Args:
            key: Unique identifier for the rate limit counter.
            limit: Maximum number of requests allowed.
            period: Window size in seconds.

        Returns:
            A tuple containing:

            (
                allowed: bool,
                remaining: int,
                reset: int,
            )
        """
        raise NotImplementedError

    @abstractmethod
    def cleanup(self, key: str | None = None):
        """Remove expired counters."""
        raise NotImplementedError
