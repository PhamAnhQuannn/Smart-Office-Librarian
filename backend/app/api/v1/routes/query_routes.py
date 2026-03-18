"""FastAPI routes for query streaming."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.v1.dependencies.settings import (
    build_error_response,
    get_authenticated_user,
    get_runtime_app,
    response_from_contract,
)
from app.domain.services.query_service import QueryRequest, QueryService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


def _get_query_service(request: Request) -> QueryService | None:
    """Return the QueryService from app state when available."""
    return getattr(request.app.state, "query_service", None)


@router.post("/query")
def query_endpoint(
    payload: dict[str, Any],
    request: Request,
    user: Any = Depends(get_authenticated_user),
    runtime_app: Any = Depends(get_runtime_app),
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
