"""In-memory query log repository with retention purge support."""

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
