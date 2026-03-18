"""Retention purge task helpers for query logs and feedback data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.logging import InMemoryStructuredLogger
from app.db.repositories.feedback_repo import InMemoryFeedbackRepository
from app.db.repositories.query_logs_repo import InMemoryQueryLogsRepository

DEFAULT_RETENTION_DAYS = 90


@dataclass(frozen=True)
class DataRetentionPurgeResult:
	retention_days: int
	purged_query_logs: int
	purged_feedback: int
	skipped_evaluation_flagged: int


class DataRetentionPurgeTaskService:
	def __init__(
		self,
		*,
		query_logs_repo: InMemoryQueryLogsRepository,
		feedback_repo: InMemoryFeedbackRepository,
		logger: InMemoryStructuredLogger | None = None,
	) -> None:
		self._query_logs_repo = query_logs_repo
		self._feedback_repo = feedback_repo
		self._logger = logger or InMemoryStructuredLogger()

	def run(self, *, now: datetime, retention_days: int = DEFAULT_RETENTION_DAYS) -> DataRetentionPurgeResult:
		if retention_days <= 0:
			raise ValueError("retention_days must be greater than zero")

		query_purge_result = self._query_logs_repo.purge_expired(
			retention_days=retention_days,
			now=now,
		)
		purged_feedback = self._feedback_repo.purge_for_query_logs(
			query_purge_result.purged_query_log_ids
		)

		self._logger.emit(
			"retention.query_logs.purged",
			retention_days=retention_days,
			cutoff_timestamp=query_purge_result.cutoff_timestamp.isoformat(),
			purged_count=len(query_purge_result.purged_query_log_ids),
			skipped_evaluation_flagged=query_purge_result.skipped_evaluation_flagged,
		)
		self._logger.emit(
			"retention.feedback.purged",
			retention_days=retention_days,
			purged_count=len(purged_feedback),
			query_log_ids=query_purge_result.purged_query_log_ids,
		)

		return DataRetentionPurgeResult(
			retention_days=retention_days,
			purged_query_logs=len(query_purge_result.purged_query_log_ids),
			purged_feedback=len(purged_feedback),
			skipped_evaluation_flagged=query_purge_result.skipped_evaluation_flagged,
		)

# ─ Celery task entry-points ────────────────────────────────────────────────────

try:
    from app.workers.celery_app import celery_app
    from app.workers.retry_policy import PURGE_RETRY_POLICY

    @celery_app.task(
        name="app.workers.tasks.purge_tasks.run_retention_purge",
        bind=True,
        max_retries=PURGE_RETRY_POLICY.max_retries,
    )
    def run_retention_purge(  # type: ignore[override]
        self,
        *,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> dict:
        """Purge expired query logs and feedback rows past the retention window."""
        import logging
        from datetime import datetime, timezone

        logger = logging.getLogger(__name__)
        try:
            query_logs_repo = InMemoryQueryLogsRepository()
            feedback_repo = InMemoryFeedbackRepository()
            service = DataRetentionPurgeTaskService(
                query_logs_repo=query_logs_repo,
                feedback_repo=feedback_repo,
            )
            result = service.run(now=datetime.now(tz=timezone.utc), retention_days=retention_days)
            logger.info("purge.completed", extra={
                "purged_query_logs": result.purged_query_logs,
                "purged_feedback": result.purged_feedback,
            })
            return {
                "status": "ok",
                "purged_query_logs": result.purged_query_logs,
                "purged_feedback": result.purged_feedback,
            }
        except Exception as exc:
            countdown = PURGE_RETRY_POLICY.countdown_for_attempt(self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)

except ImportError:
    pass  # Celery not installed in this environment