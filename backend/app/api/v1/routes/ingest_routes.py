"""FastAPI routes for ingestion job queuing."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies.settings import (
    build_error_response,
    get_authenticated_user,
    get_ingest_jobs,
)
from app.db.repositories.sources_repo import SourcesRepository
from app.db.repositories.workspaces_repo import WorkspacesRepository
from app.db.session import get_db_session

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
def ingest_endpoint(
    payload: dict[str, Any],
    user: Any = Depends(get_authenticated_user),
    ingest_jobs: dict[str, dict[str, Any]] = Depends(get_ingest_jobs),
    db: Session = Depends(get_db_session),
):
    # Admins may target any workspace by supplying workspace_id in the payload.
    target_workspace_id = user.workspace_id
    if user.is_admin and payload.get("workspace_id"):
        target_workspace_id = str(payload["workspace_id"])

    if not target_workspace_id:
        return build_error_response(
            status_code=403,
            error_code="FORBIDDEN",
            message="No workspace associated with this account",
        )

    workspace = WorkspacesRepository(db).get_by_id(target_workspace_id)
    if workspace is None:
        return build_error_response(
            status_code=403,
            error_code="WORKSPACE_NOT_FOUND",
            message="Workspace not found",
        )

    source_count = SourcesRepository(db).count_by_workspace(target_workspace_id)
    if source_count >= workspace.max_sources:
        return build_error_response(
            status_code=429,
            error_code="QUOTA_EXCEEDED",
            message=f"Source limit reached ({workspace.max_sources} sources per workspace)",
        )

    repo = str(payload.get("repo") or "").strip()
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
        "workspace_id": target_workspace_id,
        "namespace": workspace.slug,
        "status": "queued",
    }
    ingest_jobs[job_id] = record
    return JSONResponse(status_code=202, content=record)
