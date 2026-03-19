"""Query log repositories: in-memory (tests) + SQLAlchemy (production)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def _ensure_utc(value: datetime) -> datetime:
	if value.tzinfo is None:
		return value.replace(tzinfo=timezone.utc)
	return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class QueryLogRecord:
	query_log_id: str
	created_at: datetime
	evaluation_flagged: bool = False


@dataclass(frozen=True)
class QueryLogPurgeResult:
	purged_query_log_ids: list[str]
	skipped_evaluation_flagged: int
	cutoff_timestamp: datetime


class InMemoryQueryLogsRepository:
	def __init__(self, records: list[QueryLogRecord] | None = None) -> None:
		self._records: list[QueryLogRecord] = list(records or [])

	def add(self, record: QueryLogRecord) -> None:
		self._records.append(record)

	def list_all(self) -> list[QueryLogRecord]:
		return list(self._records)

	def purge_expired(self, *, retention_days: int, now: datetime) -> QueryLogPurgeResult:
		if retention_days <= 0:
			raise ValueError("retention_days must be greater than zero")

		now_utc = _ensure_utc(now)
		cutoff = now_utc - timedelta(days=retention_days)

		kept_records: list[QueryLogRecord] = []
		purged_ids: list[str] = []
		skipped_flagged = 0

		for record in self._records:
			created_at = _ensure_utc(record.created_at)
			if created_at < cutoff:
				if record.evaluation_flagged:
					kept_records.append(record)
					skipped_flagged += 1
				else:
					purged_ids.append(record.query_log_id)
				continue
			kept_records.append(record)

		self._records = kept_records

		return QueryLogPurgeResult(
			purged_query_log_ids=purged_ids,
			skipped_evaluation_flagged=skipped_flagged,
			cutoff_timestamp=cutoff,
		)


# ─ SQLAlchemy-backed production repository ─────────────────────────────────────

try:
    from typing import Any
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import Session
    from app.db.models import QueryLogModel
    from app.db.repositories.base_repo import BaseRepository

    class QueryLogsRepository(BaseRepository["QueryLogModel"]):
        model_class = QueryLogModel

        def __init__(self, session: "Session") -> None:
            super().__init__(session)

        def create(self, *, user_id: str | None, query_text: str, mode: str,
                   namespace: str, index_version: int, refusal_reason: str | None = None,
                   confidence: str | None = None, primary_cosine_score: float | None = None,
                   threshold: float | None = None, latency_ms: float | None = None,
                   ttft_ms: float | None = None, prompt_tokens: int | None = None,
                   completion_tokens: int | None = None,
                   sources: "list[dict[str, Any]] | None" = None) -> "QueryLogModel":
            log = QueryLogModel(
                user_id=user_id,
                query_text=query_text,
                mode=mode,
                namespace=namespace,
                index_version=index_version,
                refusal_reason=refusal_reason,
                confidence=confidence,
                primary_cosine_score=primary_cosine_score,
                threshold=threshold,
                latency_ms=latency_ms,
                ttft_ms=ttft_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                sources=sources,
            )
            return self.add(log)

        def list_by_user(self, user_id: str, *, limit: int = 50) -> "list[QueryLogModel]":
            stmt = (
                sa_select(QueryLogModel)
                .where(QueryLogModel.user_id == user_id)
                .order_by(QueryLogModel.created_at.desc())
                .limit(limit)
            )
            return list(self._session.scalars(stmt))

        def delete_by_id_and_user(self, log_id: str, user_id: str) -> bool:
            """Delete a single query log owned by user_id. Returns True if deleted, False if not found."""
            from sqlalchemy import delete as sa_delete
            result = self._session.execute(
                sa_delete(QueryLogModel).where(
                    QueryLogModel.id == log_id,
                    QueryLogModel.user_id == user_id,
                )
            )
            return result.rowcount > 0

        def delete_all_by_user(self, user_id: str) -> int:
            """Delete all query logs for user_id. Returns count deleted."""
            from sqlalchemy import delete as sa_delete
            result = self._session.execute(
                sa_delete(QueryLogModel).where(QueryLogModel.user_id == user_id)
            )
            return result.rowcount

except ImportError:
    pass  # SQLAlchemy not installed in this environment
