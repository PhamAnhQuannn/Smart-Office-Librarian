"""Workspace management routes.

GET    /workspace/me                  — workspace info + usage stats
GET    /workspace/sources             — list indexed sources
DELETE /workspace/sources/{source_id} — delete a source (DB only; vectors expired async)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.api.v1.dependencies.settings import build_error_response, get_authenticated_user, get_ingest_jobs
from app.db.repositories.chunks_repo import ChunksRepository
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
    request: Request,
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Return workspace details and current usage for the authenticated user."""
    workspace, err = _require_workspace(user, db)
    if err is not None:
        return err

    source_count = SourcesRepository(db).count_by_workspace(user.workspace_id)
    chunks_count = ChunksRepository(db).count_by_namespace(workspace.slug)

    # Read monthly query count from Redis (best-effort; falls back to 0)
    queries_this_month = 0
    try:
        cache = getattr(request.app.state, "cache", None)
        if cache is not None and user.workspace_id:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            key = f"workspace:{user.workspace_id}:queries:{month}"
            redis_count = cache._client.get(key)
            if redis_count is not None:
                queries_this_month = int(redis_count)
    except Exception:  # noqa: BLE001
        pass  # Redis unavailable — return 0

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
                "queries_this_month": queries_this_month,
                "chunks": chunks_count,
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


@router.delete("/sources/{source_id}", status_code=204, response_class=Response)
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
    return Response(status_code=204)


@router.post("/ingest")
def workspace_ingest(
    payload: dict[str, Any],
    request: Request,
    user: Any = Depends(get_authenticated_user),
    ingest_jobs: dict[str, dict[str, Any]] = Depends(get_ingest_jobs),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Queue an ingestion job scoped to the authenticated user's workspace.

    Accepts 'repo' or 'source_url' interchangeably for the repository identifier.
    """
    workspace, err = _require_workspace(user, db)
    if err is not None:
        return err

    source_count = SourcesRepository(db).count_by_workspace(user.workspace_id)
    if source_count >= workspace.max_sources:
        return build_error_response(
            status_code=429,
            error_code="QUOTA_EXCEEDED",
            message=f"Source limit reached ({workspace.max_sources} sources per workspace)",
        )

    repo = str(payload.get("repo") or payload.get("source_url") or "").strip()
    branch = str(payload.get("branch") or "main").strip() or "main"
    if not repo:
        return build_error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Repository identifier is required",
        )

    job_id = f"ingest-{uuid.uuid4()}"
    record: dict[str, Any] = {
        "job_id": job_id,
        "repo": repo,
        "branch": branch,
        "requested_by": user.user_id,
        "workspace_id": user.workspace_id,
        "namespace": workspace.slug,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    ingest_jobs[job_id] = record
    return JSONResponse(status_code=202, content=record)


@router.get("/ingest-runs")
def list_workspace_ingest_runs(
    request: Request,
    limit: int = 20,
    user: Any = Depends(get_authenticated_user),
) -> JSONResponse:
    """Return recent ingest runs scoped to the authenticated user's workspace, newest first."""
    if not user.workspace_id:
        return build_error_response(
            status_code=403,
            error_code="FORBIDDEN",
            message="No workspace associated with this account",
        )

    safe_limit = max(1, min(limit, 100))
    ingest_jobs: dict[str, Any] = getattr(request.app.state, "ingest_jobs", {})

    # Filter to this workspace only; reverse for newest-first
    workspace_runs = [
        {"id": k, **v}
        for k, v in ingest_jobs.items()
        if v.get("workspace_id") == user.workspace_id
    ]
    workspace_runs = list(reversed(workspace_runs))[:safe_limit]

    return JSONResponse(status_code=200, content={"items": workspace_runs})
