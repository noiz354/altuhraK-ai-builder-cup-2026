"""In-process token-bucket rate limiter for C05 public intake.

Why this exists: the donor has no rate limiting anywhere. `shared_mvp/app.py` bounds request
*size* but nothing bounds request *rate*, so public endpoints such as claim intake can be
flooded. Cloud Armor was rejected for now because the prototype does not see real traffic and an
external dependency would add a failure mode that cannot be tested locally.

Design constraints:
- Per-process, per-client, fixed-window-with-refill token bucket. No Redis, no new dependency.
- Keyed by client identity, which in this prototype is a role plus kitchen plus, when available,
  the caller's IP. IP is taken from the ASGI scope, never from a client-supplied header, so a
  caller cannot rotate an identity by forging `X-Forwarded-For` in the test client.
- Fails closed on a missing bucket rather than defaulting to allow.
- Clock is injectable so tests never sleep.

Limitation that must be stated in any claim: this is per-process. With multiple Cloud Run
instances the effective limit multiplies by the instance count. That is acceptable for a
single-instance prototype and must not be described as a DDoS control.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

# Public intake defaults: generous enough for a demo, tight enough to stop a trivial flood.
DEFAULT_CAPACITY = 30
DEFAULT_REFILL_PER_SECOND = 0.5


@dataclass
class Bucket:
    tokens: float
    updated_at: float


@dataclass
class RateLimiter:
    """Token bucket keyed by an arbitrary hashable identity.

    `limit` is the burst capacity. `per_second` is the sustained rate.
    """

    limit: int = DEFAULT_CAPACITY
    per_second: float = DEFAULT_REFILL_PER_SECOND
    clock: Callable[[], float] = time.monotonic
    _buckets: dict[object, Bucket] = field(default_factory=dict, repr=False)

    def allow(self, key: object, *, cost: float = 1.0) -> bool:
        """Consume `cost` tokens for `key`. True when the request may proceed."""
        if self.limit <= 0 or self.per_second <= 0:
            return False
        now = self.clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = Bucket(tokens=float(self.limit), updated_at=now)
            self._buckets[key] = bucket
        else:
            elapsed = max(now - bucket.updated_at, 0.0)
            bucket.tokens = min(float(self.limit), bucket.tokens + elapsed * self.per_second)
            bucket.updated_at = now
        if bucket.tokens >= cost:
            bucket.tokens -= cost
            return True
        return False

    def remaining(self, key: object) -> float:
        bucket = self._buckets.get(key)
        return float(bucket.tokens) if bucket else float(self.limit)

    def retry_after(self, key: object) -> float:
        """Seconds until one token is available. Ceiling of at least 1 second."""
        bucket = self._buckets.get(key)
        if bucket is None or bucket.tokens >= 1:
            return 0.0
        if self.per_second <= 0:
            return float('inf')
        return max(1.0, (1.0 - bucket.tokens) / self.per_second)

    def reset(self, key: object | None = None) -> None:
        if key is None:
            self._buckets.clear()
        else:
            self._buckets.pop(key, None)


def client_ip(scope) -> str:
    """Extract the peer address from an ASGI scope. Never trusts headers."""
    client = scope.get('client')
    if not client:
        return 'unknown'
    host = client[0] if isinstance(client, (list, tuple)) and client else None
    return str(host or 'unknown')


def identity(scope, *, role: str | None = None, kitchen_id: str | None = None) -> tuple:
    """Stable limiter identity: IP plus the declared tenant scope."""
    return (client_ip(scope), role or '-', kitchen_id or '-')


def scoped_endpoints_only(limiter: RateLimiter, paths: Iterable[str]):
    """Return the subset of `paths` that the limiter should protect."""
    return {p for p in paths if p}