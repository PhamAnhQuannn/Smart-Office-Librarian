"""FR-5.1 in-memory query rate limiting primitives.

Implements the canonical MVP limits from REQUIREMENTS.md:
- 50 queries per user per hour
- 5 concurrent active query streams per user
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from app.core.security import AuthenticatedUser


@dataclass(frozen=True)
class RateLimitConfig:
	max_requests_per_hour: int = 50
	max_concurrent_streams: int = 5
	window_seconds: int = 3600


class RateLimitError(Exception):
	def __init__(
		self,
		*,
		error_code: str,
		message: str,
		retry_after_seconds: int | None = None,
	) -> None:
		super().__init__(message)
		self.error_code = error_code
		self.message = message
		self.retry_after_seconds = retry_after_seconds


@dataclass
class RateLimitLease:
	user_id: str
	_limiter: "InMemoryRateLimiter"
	_released: bool = False

	def release(self) -> None:
		if self._released:
			return
		self._limiter.release(self.user_id)
		self._released = True


class InMemoryRateLimiter:
	def __init__(self, config: RateLimitConfig | None = None) -> None:
		self.config = config or RateLimitConfig()
		self._request_timestamps: dict[str, deque[float]] = {}
		self._active_streams: dict[str, int] = {}

	def acquire(self, user_id: str, *, now: float | None = None) -> RateLimitLease:
		timestamp = time.time() if now is None else now
		timestamps = self._request_timestamps.setdefault(user_id, deque())
		cutoff = timestamp - self.config.window_seconds
		while timestamps and timestamps[0] <= cutoff:
			timestamps.popleft()

		if len(timestamps) >= self.config.max_requests_per_hour:
			oldest_timestamp = timestamps[0]
			retry_after_seconds = max(
				1,
				int(oldest_timestamp + self.config.window_seconds - timestamp),
			)
			raise RateLimitError(
				error_code="RATE_LIMIT_EXCEEDED",
				message="Hourly query limit exceeded",
				retry_after_seconds=retry_after_seconds,
			)

		active_streams = self._active_streams.get(user_id, 0)
		if active_streams >= self.config.max_concurrent_streams:
			raise RateLimitError(
				error_code="RATE_LIMIT_CONCURRENCY_EXCEEDED",
				message="Concurrent stream limit exceeded",
			)

		timestamps.append(timestamp)
		self._active_streams[user_id] = active_streams + 1
		return RateLimitLease(user_id=user_id, _limiter=self)

	def release(self, user_id: str) -> None:
		active_streams = self._active_streams.get(user_id, 0)
		if active_streams <= 1:
			self._active_streams.pop(user_id, None)
			return
		self._active_streams[user_id] = active_streams - 1

	def active_streams(self, user_id: str) -> int:
		return self._active_streams.get(user_id, 0)

	def request_count(self, user_id: str, *, now: float | None = None) -> int:
		timestamp = time.time() if now is None else now
		timestamps = self._request_timestamps.setdefault(user_id, deque())
		cutoff = timestamp - self.config.window_seconds
		while timestamps and timestamps[0] <= cutoff:
			timestamps.popleft()
		return len(timestamps)


def enforce_query_rate_limit(
	user: AuthenticatedUser,
	rate_limiter: InMemoryRateLimiter,
	*,
	now: float | None = None,
) -> RateLimitLease:
	return rate_limiter.acquire(user.user_id, now=now)
