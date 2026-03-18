"""Runtime helpers for the FastAPI HTTP surface."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import Header, Request
from fastapi.responses import JSONResponse, Response

from app.api.v1.dependencies.auth import get_current_user
from app.core.logging import safe_error_message, sanitize_log_data
from app.core.security import AuthenticatedUser
from app.domain.services.health_service import HealthService


def _default_probe(_: int) -> tuple[bool, float]:
    return True, 1.0


def create_default_health_service() -> HealthService:
    return HealthService(
        postgres_probe=_default_probe,
        redis_probe=_default_probe,
        pinecone_probe=_default_probe,
    )


def get_runtime_app(request: Request) -> Any:
    return request.app.state.embedlyzer


def get_health_service(request: Request) -> HealthService:
    return request.app.state.health_service


def get_ingest_jobs(request: Request) -> dict[str, dict[str, Any]]:
    return request.app.state.ingest_jobs


def get_jwt_secret_from_state(request: Request) -> str | None:
    return getattr(request.app.state, "jwt_secret", None)


def get_authenticated_user(
    request: Request,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthenticatedUser:
    jwt_secret: str | None = getattr(request.app.state, "jwt_secret", None)
    return get_current_user(authorization or "", jwt_secret=jwt_secret)


def build_error_payload(
    *,
    status_code: int,
    error_code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error_code": error_code,
        "message": safe_error_message(message),
        "request_id": str(uuid.uuid4()),
        "details": sanitize_log_data(dict(details or {})),
    }


def build_error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            status_code=status_code,
            error_code=error_code,
            message=message,
            details=details,
        ),
        headers=dict(headers or {}),
    )


def response_from_contract(contract: Mapping[str, Any]) -> Response:
    status_code = int(contract["status_code"])
    headers = dict(contract.get("headers") or {})
    body = contract.get("body")

    if isinstance(body, str):
        return Response(content=body, status_code=status_code, headers=headers)

    # JSON body: remove content-type so JSONResponse sets it correctly
    headers.pop("Content-Type", None)
    headers.pop("content-type", None)
    return JSONResponse(content=body, status_code=status_code, headers=headers)
