"""Workspace management routes.

GET    /workspace/me                  — workspace info + usage stats
GET    /workspace/sources             — list indexed sources
DELETE /workspace/sources/{source_id} — delete a source (DB only; vectors expired async)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies.settings import build_error_response, get_authenticated_user
from app.db.repositories.sources_repo import SourcesRepository
from app.db.repositories.workspaces_repo import WorkspacesRepository
from app.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["workspace"])


def _require_workspace(user: Any, db: Session):
    """Return workspace or raise a JSONResponse error."""
    if not user.workspace_id:
        return None, build_error_response(
            status_code=403,
            error_code="FORBIDDEN",
            message="No workspace associated with this account",
        )
    workspace = WorkspacesRepository(db).get_by_id(user.workspace_id)
    if workspace is None:
        return None, build_error_response(
            status_code=404,
            error_code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
        )
    return workspace, None


@router.get("/me")
def get_workspace_me(
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Return workspace details and current usage for the authenticated user."""
    workspace, err = _require_workspace(user, db)
    if err is not None:
        return err

    source_count = SourcesRepository(db).count_by_workspace(user.workspace_id)
    return JSONResponse(
        status_code=200,
        content={
            "id": workspace.id,
            "slug": workspace.slug,
            "display_name": workspace.display_name,
            "limits": {
                "max_sources": workspace.max_sources,
                "max_chunks": workspace.max_chunks,
                "monthly_query_cap": workspace.monthly_query_cap,
            },
            "usage": {
                "sources": source_count,
            },
        },
    )


@router.get("/sources")
def list_workspace_sources(
    limit: int = 50,
    offset: int = 0,
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """List sources indexed in the authenticated user's workspace."""
    workspace, err = _require_workspace(user, db)
    if err is not None:
        return err

    sources = SourcesRepository(db).list_by_workspace(
        user.workspace_id, limit=min(limit, 200), offset=offset
    )
    return JSONResponse(
        status_code=200,
        content={
            "sources": [
                {
                    "id": s.id,
                    "repo": s.repo,
                    "file_path": s.file_path,
                    "source_url": s.source_url,
                    "last_indexed_sha": s.last_indexed_sha,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sources
            ],
            "total": SourcesRepository(db).count_by_workspace(user.workspace_id),
        },
    )


@router.delete("/sources/{source_id}", status_code=204)
def delete_workspace_source(
    source_id: str,
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
):
    """Delete a source from the workspace.

    Removes the source record from the database.
    Pinecone vector cleanup is handled asynchronously by the background worker.
    """
    workspace, err = _require_workspace(user, db)
    if err is not None:
        return err

    repo = SourcesRepository(db)
    source = repo.get_by_id_and_workspace(source_id, user.workspace_id)
    if source is None:
        return build_error_response(
            status_code=404,
            error_code="NOT_FOUND",
            message="Source not found",
        )

    repo.delete(source)
    logger.info(
        "workspace.source.deleted",
        extra={
            "source_id": source_id,
            "workspace_id": user.workspace_id,
            "namespace": workspace.slug,
        },
    )
    return None
