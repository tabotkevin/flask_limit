from dataclasses import dataclass

@dataclass(frozen=True)
class RateLimitInfo:
    limit: int
    remaining: int
    reset: int
    period: int
    key: str