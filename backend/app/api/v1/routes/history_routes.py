"""User query history routes.

GET    /history            — list the current user's past queries (newest first)
DELETE /history/{log_id}  — delete a single query log entry owned by the user
DELETE /history            — clear all query history for the current user
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.api.v1.dependencies.settings import get_authenticated_user
from app.db.session import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


def _serialize_log(log: Any) -> dict[str, Any]:
    sources = log.sources or []
    return {
        "id": log.id,
        "query_text": log.query_text,
        "confidence": log.confidence or "UNKNOWN",
        "mode": log.mode,
        "sources_count": len(sources) if isinstance(sources, list) else 0,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("")
def list_history(
    limit: int = 50,
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Return up to `limit` query log entries for the authenticated user, newest first."""
    from app.db.repositories.query_logs_repo import QueryLogsRepository

    safe_limit = max(1, min(limit, 200))
    logs = QueryLogsRepository(db).list_by_user(user.user_id, limit=safe_limit)
    return JSONResponse(
        content={
            "items": [_serialize_log(log) for log in logs],
            "total": len(logs),
        }
    )


@router.delete("/{log_id}", status_code=204, response_class=Response)
def delete_history_item(
    log_id: str,
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> Response:
    """Delete a single query history item. Raises 404 if not found or not owned by the user."""
    from app.db.repositories.query_logs_repo import QueryLogsRepository

    deleted = QueryLogsRepository(db).delete_by_id_and_user(log_id, user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History item not found")
    db.commit()
    return Response(status_code=204)


@router.delete("", status_code=204, response_class=Response)
def clear_history(
    user: Any = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> Response:
    """Delete all query history for the current user."""
    from app.db.repositories.query_logs_repo import QueryLogsRepository

    QueryLogsRepository(db).delete_all_by_user(user.user_id)
    db.commit()
    return Response(status_code=204)
