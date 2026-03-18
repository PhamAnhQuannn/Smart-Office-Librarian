"""Source metadata persistence repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import SourceModel
from app.db.repositories.base_repo import BaseRepository


class SourcesRepository(BaseRepository[SourceModel]):
    model_class = SourceModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_repo_and_path(
        self, workspace_id: str, repo: str, file_path: str
    ) -> SourceModel | None:
        stmt = select(SourceModel).where(
            SourceModel.workspace_id == workspace_id,
            SourceModel.repo == repo,
            SourceModel.file_path == file_path,
        )
        return self._session.scalars(stmt).first()

    def list_by_workspace(
        self, workspace_id: str, *, limit: int = 100, offset: int = 0
    ) -> list[SourceModel]:
        stmt = (
            select(SourceModel)
            .where(SourceModel.workspace_id == workspace_id)
            .order_by(SourceModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def count_by_workspace(self, workspace_id: str) -> int:
        stmt = select(func.count()).select_from(SourceModel).where(
            SourceModel.workspace_id == workspace_id
        )
        return self._session.scalar(stmt) or 0

    def get_by_id_and_workspace(
        self, source_id: str, workspace_id: str
    ) -> SourceModel | None:
        stmt = select(SourceModel).where(
            SourceModel.id == source_id,
            SourceModel.workspace_id == workspace_id,
        )
        return self._session.scalars(stmt).first()

    def upsert(
        self,
        *,
        workspace_id: str,
        repo: str,
        file_path: str,
        source_url: str | None,
    ) -> SourceModel:
        existing = self.get_by_repo_and_path(workspace_id, repo, file_path)
        if existing:
            existing.source_url = source_url
            self._session.flush()
            return existing
        return self.add(SourceModel(
            workspace_id=workspace_id,
            repo=repo,
            file_path=file_path,
            source_url=source_url,
        ))

    def update_last_indexed_sha(self, source_id: str, sha: str) -> None:
        source = self._session.get(SourceModel, source_id)
        if source:
            source.last_indexed_sha = sha
            self._session.flush()
