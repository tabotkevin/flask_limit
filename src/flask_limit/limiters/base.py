from abc import ABC, abstractmethod

BACKEND_REGISTRY: dict[str, type["Limiter"]] = {}


class LimiterException(Exception):
    pass


class Limiter(ABC):

    def __init_subclass__(cls, name: str | None = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        if name:
            BACKEND_REGISTRY[name] = cls

    @classmethod
    @abstractmethod
    def from_app(cls, app):
        """Construct the backend using the Flask application configuration."""
        raise NotImplementedError

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
