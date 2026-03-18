"""Workspace persistence repository."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import WorkspaceModel
from app.db.repositories.base_repo import BaseRepository


def _make_slug(owner_id: str) -> str:
    """Derive a URL-safe Pinecone namespace slug from the owner UUID."""
    # Use first 8 hex chars of the UUID (already lowercase alphanum)
    return re.sub(r"[^a-z0-9-]", "", owner_id.replace("-", ""))[:24]


class WorkspacesRepository(BaseRepository[WorkspaceModel]):
    model_class = WorkspaceModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, *, owner_id: str, display_name: str) -> WorkspaceModel:
        slug = _make_slug(owner_id)
        workspace = WorkspaceModel(
            owner_id=owner_id,
            slug=slug,
            display_name=display_name,
        )
        return self.add(workspace)

    def get_by_owner(self, owner_id: str) -> WorkspaceModel | None:
        stmt = select(WorkspaceModel).where(WorkspaceModel.owner_id == owner_id)
        return self._session.scalars(stmt).first()

    def get_by_slug(self, slug: str) -> WorkspaceModel | None:
        stmt = select(WorkspaceModel).where(WorkspaceModel.slug == slug)
        return self._session.scalars(stmt).first()

    def get_by_id(self, workspace_id: str) -> WorkspaceModel | None:
        return self._session.get(WorkspaceModel, workspace_id)
