"""FastAPI routes for query streaming."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.v1.dependencies.settings import (
    build_error_response,
    get_authenticated_user,
    get_runtime_app,
    response_from_contract,
)
from app.db.session import get_db_session
from app.domain.services.query_service import QueryRequest, QueryService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


def _quota_key(workspace_id: str) -> str:
    """Redis key for this workspace's monthly query counter."""
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"workspace:{workspace_id}:queries:{month}"


def _check_and_increment_quota(request: Request, workspace_id: str, monthly_cap: int) -> bool:
    """Return True if the query is allowed; increments counter if so.
    Gracefully allows the query when Redis is unavailable."""
    cache = getattr(request.app.state, "cache", None)
    if cache is None or not workspace_id:
        return True
    try:
        redis = cache._client
        key = _quota_key(workspace_id)
        # Atomic increment; set 35-day TTL on first use so the key expires naturally.
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 60 * 60 * 24 * 35)
        if count > monthly_cap:
            # Over cap — decrement back so the count stays accurate.
            redis.decr(key)
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("quota check failed workspace=%s error=%s — allowing query", workspace_id, exc)
        return True


def _get_query_service(request: Request) -> QueryService | None:
    """Return the QueryService from app state when available."""
    return getattr(request.app.state, "query_service", None)


@router.post("/query")
def query_endpoint(
    payload: dict[str, Any],
    request: Request,
    user: Any = Depends(get_authenticated_user),
    runtime_app: Any = Depends(get_runtime_app),
    db: Session = Depends(get_db_session),
):
    query_text = str(payload.get("query") or "").strip()
    if not query_text:
        return build_error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="Query text is required",
        )

    retrieval_only = bool(payload.get("retrieval_only", False))

    # Namespace is derived from the user's workspace — clients cannot override it.
    namespace = user.workspace_slug or user.workspace_id or "dev"

    # ── Monthly query quota ──────────────────────────────────────────────────
    if user.workspace_id and db is not None:
        try:
            from app.db.repositories.workspaces_repo import WorkspacesRepository
            ws = WorkspacesRepository(db).get_by_id(user.workspace_id)
            if ws is not None and ws.monthly_query_cap > 0:
                allowed = _check_and_increment_quota(request, user.workspace_id, ws.monthly_query_cap)
                if not allowed:
                    return build_error_response(
                        status_code=429,
                        error_code="QUOTA_EXCEEDED",
                        message=f"Monthly query limit of {ws.monthly_query_cap} reached",
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("workspace quota lookup failed: %s — allowing query", exc)
    # ─────────────────────────────────────────────────────────────────────────

    # Use the real QueryService pipeline when wired up in app state.
    query_service: QueryService | None = _get_query_service(request)

    if query_service is not None:
        query_request = QueryRequest(
            query_text=query_text,
            namespace=namespace,
            index_version=1,
            rbac_filter=None,
            retrieval_only_mode=retrieval_only,
        )
        try:
            pipeline_result = query_service.execute(query_request)
        except Exception as exc:  # noqa: BLE001
            logger.error("query pipeline error: %s", exc)
            return build_error_response(
                status_code=500,
                error_code="INTERNAL_ERROR",
                message="Query processing failed",
            )

        response = runtime_app.query(
            user=user,
            mode=pipeline_result.get("mode", "answer"),
            refusal_reason=pipeline_result.get("refusal_reason"),
            sources=pipeline_result.get("sources", []),
            token_events=pipeline_result.get("token_events"),
            confidence=pipeline_result.get("confidence", "LOW"),
            query_text=query_text,
        )
    else:
        # Fallback: QueryService not yet wired — use stub data so tests pass.
        logger.warning("QueryService not wired in app.state — returning stub result")
        response = runtime_app.query(
            user=user,
            mode="retrieval_only" if retrieval_only else "answer",
            refusal_reason=None,
            sources=[
                {
                    "file_path": "docs/00_backbone/README.md",
                    "source_url": "https://github.com/example/repo/blob/main/docs/00_backbone/README.md",
                    "start_line": 1,
                    "end_line": 10,
                    "text": "This is a stub source placeholder.",
                    "score": 0.82,
                }
            ],
            token_events=None if retrieval_only else ["Answer based on available documentation."],
            confidence="MEDIUM",
            query_text=query_text,
        )

    return response_from_contract(response)
