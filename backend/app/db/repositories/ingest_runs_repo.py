"""Ingest run persistence repository."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IngestRunModel
from app.db.repositories.base_repo import BaseRepository


class IngestRunsRepository(BaseRepository[IngestRunModel]):
    model_class = IngestRunModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, *, repo: str, branch: str = "main",
               requested_by: str | None = None) -> IngestRunModel:
        run = IngestRunModel(repo=repo, branch=branch, requested_by=requested_by)
        return self.add(run)

    def mark_running(self, run_id: str) -> None:
        run = self._session.get(IngestRunModel, run_id)
        if run:
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            self._session.flush()

    def mark_completed(self, run_id: str, *, ingested: int, purged: int,
                       skipped: int) -> None:
        run = self._session.get(IngestRunModel, run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.ingested_documents = ingested
            run.purged_paths = purged
            run.skipped_duplicates = skipped
            self._session.flush()

    def mark_failed(self, run_id: str, *, error_message: str) -> None:
        run = self._session.get(IngestRunModel, run_id)
        if run:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = error_message
            self._session.flush()

    def list_by_repo(self, repo: str, *, limit: int = 20) -> list[IngestRunModel]:
        stmt = (
            select(IngestRunModel)
            .where(IngestRunModel.repo == repo)
            .order_by(IngestRunModel.created_at.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))
