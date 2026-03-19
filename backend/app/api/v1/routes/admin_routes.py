"""Focused admin-route helpers for audit logging and retention foundation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.dependencies.settings import build_error_response, get_authenticated_user
from app.core.logging import AUDIT_LOG_RETENTION_DAYS, InMemoryStructuredLogger
from app.core.security import AuthenticatedUser
from app.db.session import get_db_session

router = APIRouter(prefix="/admin", tags=["admin"])


@dataclass(frozen=True)
class AdminRouteError(Exception):
    error_code: str
    message: str
    status_code: int

    def __str__(self) -> str:
        return self.message


def _get_actor_value(actor: Any, field_name: str) -> Any:
    if isinstance(actor, Mapping):
        return actor.get(field_name)
    return getattr(actor, field_name, None)


def _normalize_role(role: Any) -> str:
    if hasattr(role, "value"):
        return str(role.value).lower()
    return str(role).lower()


def _require_admin(actor: Any) -> tuple[str, Any]:
    actor_id = _get_actor_value(actor, "user_id") or _get_actor_value(actor, "id")
    if not actor_id:
        raise AdminRouteError("UNAUTHENTICATED", "Authentication required", 401)

    role = _get_actor_value(actor, "role")
    if _normalize_role(role) != "admin":
        raise AdminRouteError("FORBIDDEN", "Admin role required", 403)

    return str(actor_id), role


def update_source_configuration(
    source_id: str,
    updates: Mapping[str, Any],
    *,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    actor_id, actor_role = _require_admin(actor)
    normalized_updates = dict(updates)
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="source",
        action="updated",
        resource_id=source_id,
        changes=normalized_updates,
    )
    return {
        "source_id": source_id,
        "updated_fields": sorted(normalized_updates.keys()),
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


def delete_source_configuration(
    source_id: str,
    *,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    actor_id, actor_role = _require_admin(actor)
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="source",
        action="deleted",
        resource_id=source_id,
        changes={"source_id": source_id},
    )
    return {
        "source_id": source_id,
        "status": "queued_for_deletion",
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


def update_threshold_configuration(
    *,
    namespace: str,
    index_version: int,
    threshold: float,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    if threshold < 0.0 or threshold > 1.0:
        raise AdminRouteError("VALIDATION_ERROR", "Threshold must be between 0.0 and 1.0", 400)

    actor_id, actor_role = _require_admin(actor)
    resource_id = f"{namespace}:{index_version}"
    changes = {
        "namespace": namespace,
        "index_version": index_version,
        "threshold": threshold,
    }
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="threshold",
        action="updated",
        resource_id=resource_id,
        changes=changes,
    )
    return {
        "namespace": namespace,
        "index_version": index_version,
        "threshold": threshold,
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


def update_role_assignment(
    target_user_id: str,
    new_role: str,
    *,
    actor: Any,
    logger: InMemoryStructuredLogger,
) -> dict[str, Any]:
    """Emit an audit event when an admin assigns a role to a user."""
    actor_id, actor_role = _require_admin(actor)
    changes = {
        "target_user_id": target_user_id,
        "new_role": new_role,
    }
    logger.log_admin_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        resource_type="role",
        action="assigned",
        resource_id=target_user_id,
        changes=changes,
    )
    return {
        "target_user_id": target_user_id,
        "new_role": new_role,
        "audit_retention_days": AUDIT_LOG_RETENTION_DAYS,
    }


# ─ FastAPI HTTP handlers ───────────────────────────────────────────────────────

def _get_logger(request: Request) -> InMemoryStructuredLogger:
    return getattr(request.app.state, "logger", InMemoryStructuredLogger())


@router.get("/thresholds", summary="List all threshold configs")
def list_thresholds(
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    threshold_service = getattr(request.app.state, "threshold_service", None)
    if threshold_service is None:
        return JSONResponse(status_code=200, content={"thresholds": []})

    try:
        thresholds = threshold_service.list_all() if hasattr(threshold_service, "list_all") else []
        return JSONResponse(status_code=200, content={"thresholds": thresholds})
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.put("/thresholds", summary="Update similarity threshold for a namespace")
def put_threshold(
    payload: dict[str, Any],
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    namespace = str(payload.get("namespace") or "").strip()
    index_version = payload.get("index_version")
    threshold = payload.get("threshold")

    if not namespace:
        return build_error_response(status_code=422, error_code="VALIDATION_ERROR", message="namespace is required")
    if index_version is None:
        return build_error_response(status_code=422, error_code="VALIDATION_ERROR", message="index_version is required")
    if threshold is None:
        return build_error_response(status_code=422, error_code="VALIDATION_ERROR", message="threshold is required")

    try:
        result = update_threshold_configuration(
            namespace=namespace,
            index_version=int(index_version),
            threshold=float(threshold),
            actor=user,
            logger=_get_logger(request),
        )
        threshold_service = getattr(request.app.state, "threshold_service", None)
        if threshold_service is not None:
            threshold_service.update_threshold(
                namespace=namespace,
                index_version=int(index_version),
                threshold=float(threshold),
                updated_by=user.user_id,
            )
        return JSONResponse(status_code=200, content=result)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.get("/sources", summary="List all ingested sources")
def list_sources(
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    sources_repo = getattr(request.app.state, "sources_repo", None)
    if sources_repo is None:
        return JSONResponse(status_code=200, content={"sources": [], "total": 0})

    try:
        items = sources_repo.list(limit=limit, offset=offset)
        return JSONResponse(
            status_code=200,
            content={"sources": [{"id": str(s.id), "repo": getattr(s, "repo", ""), "branch": getattr(s, "branch", "")} for s in items]},
        )
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.delete("/sources/{source_id}", summary="Delete a source and its chunks")
def delete_source(
    source_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
) -> JSONResponse:
    try:
        result = delete_source_configuration(source_id=source_id, actor=user, logger=_get_logger(request))
        return JSONResponse(status_code=200, content=result)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.get("/audit-logs", summary="List recent audit log entries")
def list_audit_logs(
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    limit: int = 100,
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    audit_repo = getattr(request.app.state, "audit_repo", None)
    if audit_repo is None:
        logger = _get_logger(request)
        return JSONResponse(status_code=200, content={"audit_logs": logger._events[-limit:] if hasattr(logger, "_events") else []})

    try:
        items = audit_repo.list(limit=limit, offset=0)
        return JSONResponse(
            status_code=200,
            content={"audit_logs": [{"id": str(i.id), "action": getattr(i, "action", ""), "actor_id": getattr(i, "actor_id", "")} for i in items]},
        )
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.get("/evaluation/summary", summary="Analytics summary from query logs")
def get_evaluation_summary(
    range: str = "7d",
    request: Request = None,  # type: ignore[assignment]
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Return aggregated analytics from the query_logs table for the given date range."""
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    from collections import Counter
    from datetime import datetime, timedelta, timezone

    from app.db.models import QueryLogModel

    now = datetime.now(timezone.utc)
    since: datetime | None
    if range == "7d":
        since = now - timedelta(days=7)
        days_count = 7
    elif range == "30d":
        since = now - timedelta(days=30)
        days_count = 30
    else:
        since = None
        days_count = 30

    query = db.query(QueryLogModel)
    if since is not None:
        query = query.filter(QueryLogModel.created_at >= since)
    logs = query.all()

    total = len(logs)
    confidence_high = sum(1 for lg in logs if (lg.confidence or "").upper() == "HIGH")
    confidence_medium = sum(1 for lg in logs if (lg.confidence or "").upper() == "MEDIUM")
    confidence_refused = sum(1 for lg in logs if (lg.confidence or "").upper() in ("REFUSED", "LOW"))
    pass_count = confidence_high + confidence_medium
    fail_count = confidence_refused

    token_usage = sum(
        (lg.prompt_tokens or 0) + (lg.completion_tokens or 0) for lg in logs
    )

    latencies = [lg.latency_ms for lg in logs if lg.latency_ms is not None]
    latencies_sorted = sorted(latencies)
    p50_ms: float | None = None
    p95_ms: float | None = None
    if latencies_sorted:
        p50_ms = latencies_sorted[len(latencies_sorted) // 2]
        p95_ms = latencies_sorted[min(int(len(latencies_sorted) * 0.95), len(latencies_sorted) - 1)]

    # Daily volume array (oldest → newest)
    day_counter: Counter = Counter()
    for lg in logs:
        if lg.created_at:
            day_counter[lg.created_at.date()] += 1
    volume_by_day = [
        day_counter.get((now - timedelta(days=days_count - 1 - i)).date(), 0)
        for i in range(days_count)
    ]

    # Latency sparkline (last 14 average-by-day)
    sparkline_days = 14
    sparkline: list[float] = []
    for i in range(sparkline_days):
        d = (now - timedelta(days=sparkline_days - 1 - i)).date()
        day_lats = [lg.latency_ms for lg in logs if lg.latency_ms and lg.created_at and lg.created_at.date() == d]
        sparkline.append(sum(day_lats) / len(day_lats) if day_lats else 0.0)

    return JSONResponse(status_code=200, content={
        "total": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": round(pass_count / total, 3) if total > 0 else 0.0,
        "namespace": "all",
        "index_version": None,
        "token_usage": token_usage,
        "token_budget": 1_000_000,
        "confidence_high": confidence_high,
        "confidence_medium": confidence_medium,
        "confidence_refused": confidence_refused,
        "volume_by_day": volume_by_day,
        "p50_ms": round(p50_ms, 1) if p50_ms is not None else None,
        "p95_ms": round(p95_ms, 1) if p95_ms is not None else None,
        "latency_sparkline": sparkline,
    })


@router.get("/budget", summary="List all workspaces with budget limits")
def list_budget(
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Return all workspaces with their monthly query cap and current-month usage."""
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    from datetime import datetime, timezone

    from app.db.models import QueryLogModel, WorkspaceModel

    workspaces = db.query(WorkspaceModel).all()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    items = []
    for ws in workspaces:
        used_this_month = (
            db.query(QueryLogModel)
            .filter(
                QueryLogModel.namespace == ws.slug,
                QueryLogModel.created_at >= month_start,
            )
            .count()
        )
        items.append({
            "id": ws.id,
            "slug": ws.slug,
            "display_name": ws.display_name,
            "monthly_query_cap": ws.monthly_query_cap,
            "used_this_month": used_this_month,
            "max_sources": ws.max_sources,
            "max_chunks": ws.max_chunks,
        })

    return JSONResponse(status_code=200, content={"workspaces": items})


@router.put("/budget/{workspace_id}", summary="Update workspace query cap")
def update_budget(
    workspace_id: str,
    payload: dict[str, Any],
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    """Update monthly_query_cap for a workspace."""
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    from app.db.models import WorkspaceModel

    ws = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
    if not ws:
        return build_error_response(status_code=404, error_code="NOT_FOUND", message="Workspace not found")

    cap = payload.get("monthly_query_cap")
    if cap is None or not isinstance(cap, int) or cap < 0:
        return build_error_response(status_code=422, error_code="VALIDATION_ERROR", message="monthly_query_cap must be a non-negative integer")

    ws.monthly_query_cap = cap
    db.commit()
    return JSONResponse(status_code=200, content={"id": workspace_id, "monthly_query_cap": cap})


@router.get("/ingest-runs", summary="List recent ingest run records")
def list_ingest_runs(
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    limit: int = 50,
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    ingest_runs_repo = getattr(request.app.state, "ingest_runs_repo", None)
    if ingest_runs_repo is None:
        ingest_jobs = getattr(request.app.state, "ingest_jobs", {})
        runs = [{"job_id": k, **v} for k, v in list(ingest_jobs.items())[-limit:]]
        return JSONResponse(status_code=200, content={"ingest_runs": runs})

    try:
        items = ingest_runs_repo.list(limit=limit, offset=0)
        return JSONResponse(
            status_code=200,
            content={"ingest_runs": [{"id": str(i.id), "status": getattr(i, "status", "")} for i in items]},
        )
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


# ─ Workspace management (admin-only) ──────────────────────────────────────────

@router.get("/workspaces", summary="List all workspaces")
def list_workspaces(
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    try:
        from app.db.repositories.workspaces_repo import WorkspacesRepository
        from app.db.repositories.sources_repo import SourcesRepository

        ws_repo = WorkspacesRepository(db)
        workspaces = ws_repo.list(limit=min(limit, 200), offset=offset)
        src_repo = SourcesRepository(db)
        return JSONResponse(
            status_code=200,
            content={
                "workspaces": [
                    {
                        "id": ws.id,
                        "slug": ws.slug,
                        "display_name": ws.display_name,
                        "owner_id": ws.owner_id,
                        "source_count": src_repo.count_by_workspace(ws.id),
                        "limits": {
                            "max_sources": ws.max_sources,
                            "max_chunks": ws.max_chunks,
                            "monthly_query_cap": ws.monthly_query_cap,
                        },
                        "created_at": ws.created_at.isoformat() if ws.created_at else None,
                    }
                    for ws in workspaces
                ],
            },
        )
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.get("/workspaces/{workspace_id}", summary="Get a workspace by ID")
def get_workspace(
    workspace_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    try:
        from app.db.repositories.workspaces_repo import WorkspacesRepository
        from app.db.repositories.sources_repo import SourcesRepository

        ws = WorkspacesRepository(db).get_by_id(workspace_id)
        if ws is None:
            return build_error_response(status_code=404, error_code="NOT_FOUND", message="Workspace not found")

        source_count = SourcesRepository(db).count_by_workspace(workspace_id)
        return JSONResponse(
            status_code=200,
            content={
                "id": ws.id,
                "slug": ws.slug,
                "display_name": ws.display_name,
                "owner_id": ws.owner_id,
                "source_count": source_count,
                "limits": {
                    "max_sources": ws.max_sources,
                    "max_chunks": ws.max_chunks,
                    "monthly_query_cap": ws.monthly_query_cap,
                },
                "created_at": ws.created_at.isoformat() if ws.created_at else None,
                "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
            },
        )
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.put("/workspaces/{workspace_id}/limits", summary="Update workspace resource limits")
def update_workspace_limits(
    workspace_id: str,
    payload: dict[str, Any],
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    try:
        from app.db.repositories.workspaces_repo import WorkspacesRepository

        ws = WorkspacesRepository(db).get_by_id(workspace_id)
        if ws is None:
            return build_error_response(status_code=404, error_code="NOT_FOUND", message="Workspace not found")

        updated_fields: dict[str, Any] = {}
        if "max_sources" in payload:
            ws.max_sources = int(payload["max_sources"])
            updated_fields["max_sources"] = ws.max_sources
        if "max_chunks" in payload:
            ws.max_chunks = int(payload["max_chunks"])
            updated_fields["max_chunks"] = ws.max_chunks
        if "monthly_query_cap" in payload:
            ws.monthly_query_cap = int(payload["monthly_query_cap"])
            updated_fields["monthly_query_cap"] = ws.monthly_query_cap

        db.flush()
        db.commit()

        _get_logger(request).log_admin_audit_event(
            actor_id=user.user_id,
            actor_role=user.role,
            resource_type="workspace",
            action="limits_updated",
            resource_id=workspace_id,
            changes=updated_fields,
        )

        return JSONResponse(
            status_code=200,
            content={
                "workspace_id": workspace_id,
                "updated_fields": updated_fields,
            },
        )
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))


@router.delete("/workspaces/{workspace_id}", summary="Delete a workspace and all its data")
def delete_workspace(
    workspace_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(get_authenticated_user),
    db: Session = Depends(get_db_session),
) -> JSONResponse:
    try:
        _require_admin(user)
    except AdminRouteError as exc:
        return build_error_response(status_code=exc.status_code, error_code=exc.error_code, message=exc.message)

    try:
        from app.db.repositories.workspaces_repo import WorkspacesRepository

        ws = WorkspacesRepository(db).get_by_id(workspace_id)
        if ws is None:
            return build_error_response(status_code=404, error_code="NOT_FOUND", message="Workspace not found")

        slug = ws.slug
        db.delete(ws)
        db.commit()

        _get_logger(request).log_admin_audit_event(
            actor_id=user.user_id,
            actor_role=user.role,
            resource_type="workspace",
            action="deleted",
            resource_id=workspace_id,
            changes={"slug": slug},
        )

        return JSONResponse(status_code=200, content={"workspace_id": workspace_id, "slug": slug, "status": "deleted"})
    except Exception as exc:
        return build_error_response(status_code=500, error_code="INTERNAL_ERROR", message=str(exc))

