from __future__ import annotations

import pytest

from app.api.v1.dependencies.rate_limit import (
    InMemoryRateLimiter,
    RateLimitError,
    enforce_query_rate_limit,
)
from app.core.security import AuthenticatedUser, UserRole


def test_rate_limiter_allows_up_to_fifty_queries_per_hour_and_releases_streams() -> None:
    limiter = InMemoryRateLimiter()

    for attempt in range(50):
        lease = limiter.acquire("user-1", now=1000.0 + attempt)
        assert limiter.active_streams("user-1") == 1
        lease.release()
        assert limiter.active_streams("user-1") == 0

    assert limiter.request_count("user-1", now=1049.0) == 50


def test_rate_limiter_rejects_fifty_first_query_with_retry_after() -> None:
    limiter = InMemoryRateLimiter()

    for attempt in range(50):
        limiter.acquire("user-1", now=1000.0 + attempt).release()

    with pytest.raises(RateLimitError) as exc_info:
        limiter.acquire("user-1", now=1051.0)

    assert exc_info.value.error_code == "RATE_LIMIT_EXCEEDED"
    assert exc_info.value.retry_after_seconds == 3549


def test_rate_limiter_rejects_sixth_concurrent_stream() -> None:
    limiter = InMemoryRateLimiter()
    leases = [limiter.acquire("user-1", now=1000.0 + attempt) for attempt in range(5)]

    with pytest.raises(RateLimitError) as exc_info:
        limiter.acquire("user-1", now=1006.0)

    assert exc_info.value.error_code == "RATE_LIMIT_CONCURRENCY_EXCEEDED"

    for lease in leases:
        lease.release()

    assert limiter.active_streams("user-1") == 0


def test_enforce_query_rate_limit_uses_authenticated_user_id() -> None:
    limiter = InMemoryRateLimiter()
    user = AuthenticatedUser(user_id="auth-user", role=UserRole.USER)

    lease = enforce_query_rate_limit(user, limiter, now=2000.0)

    assert limiter.request_count("auth-user", now=2000.0) == 1
    lease.release()
