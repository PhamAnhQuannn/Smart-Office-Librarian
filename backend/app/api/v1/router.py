"""FastAPI router registration for HTTP runtime endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.v1.dependencies.settings import (
    build_error_response,
    get_authenticated_user,
    get_runtime_app,
    response_from_contract,
)
from app.api.v1.routes.admin_routes import router as admin_router
from app.api.v1.routes.auth_routes import router as auth_router
from app.api.v1.routes.feedback_routes import FeedbackSubmission, submit_feedback
from app.api.v1.routes.health_routes import router as health_router
from app.api.v1.routes.history_routes import router as history_router
from app.api.v1.routes.ingest_routes import router as ingest_router
from app.api.v1.routes.metrics_routes import get_metrics_response
from app.api.v1.routes.query_routes import router as query_router
from app.api.v1.routes.workspace_routes import router as workspace_router

api_router = APIRouter()
ops_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(query_router)
api_router.include_router(ingest_router)
api_router.include_router(workspace_router)
api_router.include_router(history_router)
api_router.include_router(health_router)
api_router.include_router(admin_router)
ops_router.include_router(health_router)


@api_router.post("/feedback")
def feedback_endpoint(
    payload: dict[str, Any],
    user: Any = Depends(get_authenticated_user),
    runtime_app: Any = Depends(get_runtime_app),
):
    query_log_id = str(payload.get("query_log_id") or "").strip()
    feedback = payload.get("feedback")

    if not query_log_id:
        return build_error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="query_log_id is required",
        )
    if feedback not in (1, -1):
        return build_error_response(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message="feedback must be 1 or -1",
        )

    vote = "up" if feedback == 1 else "down"
    response = submit_feedback(
        FeedbackSubmission(
            query_log_id=query_log_id,
            vote=vote,
            comment=payload.get("comment"),
            metadata=payload.get("metadata"),
        ),
        user=user,
        logger=runtime_app.logger,
        metrics=runtime_app.metrics,
    )
    return response_from_contract(response)


@api_router.get("/metrics")
@ops_router.get("/metrics")
def metrics_endpoint(runtime_app: Any = Depends(get_runtime_app)):
    return response_from_contract(get_metrics_response(runtime_app.metrics))
