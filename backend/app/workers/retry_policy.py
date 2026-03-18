"""Reusable Celery retry configuration presets."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    countdown_seconds: int
    backoff_factor: float = 2.0

    def countdown_for_attempt(self, attempt: int) -> int:
        """Exponential back-off capped at 10 minutes."""
        delay = self.countdown_seconds * (self.backoff_factor ** attempt)
        return min(int(delay), 600)


# Pre-defined policies
INGEST_RETRY_POLICY = RetryPolicy(max_retries=3, countdown_seconds=60)
BACKUP_RETRY_POLICY = RetryPolicy(max_retries=2, countdown_seconds=120)
REINDEX_RETRY_POLICY = RetryPolicy(max_retries=2, countdown_seconds=120)
PURGE_RETRY_POLICY = RetryPolicy(max_retries=3, countdown_seconds=30)
