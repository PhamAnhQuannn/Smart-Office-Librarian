"""Feedback repositories: in-memory (tests) + SQLAlchemy (production)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class FeedbackRecord:
	feedback_id: str
	query_log_id: str
	created_at: datetime
	vote: str
	comment: str | None = None


class InMemoryFeedbackRepository:
	def __init__(self, records: list[FeedbackRecord] | None = None) -> None:
		self._records: list[FeedbackRecord] = list(records or [])

	def add(self, record: FeedbackRecord) -> None:
		self._records.append(record)

	def list_all(self) -> list[FeedbackRecord]:
		return list(self._records)

	def purge_for_query_logs(self, query_log_ids: Iterable[str]) -> list[FeedbackRecord]:
		purge_ids = set(query_log_ids)
		if not purge_ids:
			return []

		purged: list[FeedbackRecord] = []
		kept: list[FeedbackRecord] = []

		for record in self._records:
			if record.query_log_id in purge_ids:
				purged.append(record)
				continue
			kept.append(record)

		self._records = kept
		return purged


# ─ SQLAlchemy-backed production repository ─────────────────────────────────────

try:
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.db.models import FeedbackModel
    from app.db.repositories.base_repo import BaseRepository

    class FeedbackRepository(BaseRepository["FeedbackModel"]):
        model_class = FeedbackModel

        def __init__(self, session: "Session") -> None:
            super().__init__(session)

        def create(self, *, query_log_id: str, vote: str, user_id: str | None = None,
                   comment: str | None = None) -> "FeedbackModel":
            fb = FeedbackModel(
                query_log_id=query_log_id,
                vote=vote,
                user_id=user_id,
                comment=comment,
            )
            return self.add(fb)

        def list_by_query_log(self, query_log_id: str) -> list["FeedbackModel"]:
            stmt = select(FeedbackModel).where(FeedbackModel.query_log_id == query_log_id)
            return list(self._session.scalars(stmt))

except ImportError:
    pass  # SQLAlchemy not installed in this environment

