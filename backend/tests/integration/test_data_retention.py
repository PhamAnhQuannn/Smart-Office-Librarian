from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging import InMemoryStructuredLogger
from app.db.repositories.feedback_repo import FeedbackRecord, InMemoryFeedbackRepository
from app.db.repositories.query_logs_repo import InMemoryQueryLogsRepository, QueryLogRecord
from app.workers.tasks.purge_tasks import DataRetentionPurgeTaskService


def test_data_retention_purges_old_query_logs_and_feedback_with_audit_log() -> None:
    now = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)
    query_logs = InMemoryQueryLogsRepository(
        records=[
            QueryLogRecord(query_log_id="old-purge", created_at=now - timedelta(days=91)),
            QueryLogRecord(
                query_log_id="old-flagged",
                created_at=now - timedelta(days=140),
                evaluation_flagged=True,
            ),
            QueryLogRecord(query_log_id="recent-keep", created_at=now - timedelta(days=15)),
        ]
    )
    feedback = InMemoryFeedbackRepository(
        records=[
            FeedbackRecord(
                feedback_id="fb-1",
                query_log_id="old-purge",
                created_at=now - timedelta(days=90),
                vote="down",
            ),
            FeedbackRecord(
                feedback_id="fb-2",
                query_log_id="recent-keep",
                created_at=now - timedelta(days=2),
                vote="up",
            ),
            FeedbackRecord(
                feedback_id="fb-3",
                query_log_id="old-flagged",
                created_at=now - timedelta(days=80),
                vote="down",
            ),
        ]
    )
    logger = InMemoryStructuredLogger()
    task = DataRetentionPurgeTaskService(
        query_logs_repo=query_logs,
        feedback_repo=feedback,
        logger=logger,
    )

    result = task.run(now=now, retention_days=90)

    assert result.retention_days == 90
    assert result.purged_query_logs == 1
    assert result.purged_feedback == 1
    assert result.skipped_evaluation_flagged == 1

    remaining_query_log_ids = {record.query_log_id for record in query_logs.list_all()}
    assert remaining_query_log_ids == {"old-flagged", "recent-keep"}

    remaining_feedback_ids = {record.feedback_id for record in feedback.list_all()}
    assert remaining_feedback_ids == {"fb-2", "fb-3"}

    query_log_entry = logger.entries[-2]
    assert query_log_entry.event_type == "retention.query_logs.purged"
    assert query_log_entry.payload["purged_count"] == 1
    assert query_log_entry.payload["skipped_evaluation_flagged"] == 1

    feedback_entry = logger.entries[-1]
    assert feedback_entry.event_type == "retention.feedback.purged"
    assert feedback_entry.payload["purged_count"] == 1
    assert feedback_entry.payload["query_log_ids"] == ["old-purge"]


def test_data_retention_window_is_configurable_and_keeps_records_within_window() -> None:
    now = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)
    query_logs = InMemoryQueryLogsRepository(
        records=[
            QueryLogRecord(query_log_id="older-than-30", created_at=now - timedelta(days=31)),
            QueryLogRecord(query_log_id="within-30", created_at=now - timedelta(days=29)),
        ]
    )
    feedback = InMemoryFeedbackRepository(
        records=[
            FeedbackRecord(
                feedback_id="fb-old",
                query_log_id="older-than-30",
                created_at=now - timedelta(days=20),
                vote="down",
            ),
            FeedbackRecord(
                feedback_id="fb-recent",
                query_log_id="within-30",
                created_at=now - timedelta(days=5),
                vote="up",
            ),
        ]
    )
    task = DataRetentionPurgeTaskService(
        query_logs_repo=query_logs,
        feedback_repo=feedback,
    )

    result = task.run(now=now, retention_days=30)

    assert result.purged_query_logs == 1
    assert result.purged_feedback == 1

    remaining_query_logs = {record.query_log_id for record in query_logs.list_all()}
    assert remaining_query_logs == {"within-30"}

    remaining_feedback = {record.feedback_id for record in feedback.list_all()}
    assert remaining_feedback == {"fb-recent"}