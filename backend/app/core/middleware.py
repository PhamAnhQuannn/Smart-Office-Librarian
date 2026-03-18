"""ASGI middleware for the FastAPI application.

Provides:
- CORSMiddleware configuration
- X-Request-ID injection (generate if not present in request headers)
- Structured access logging for every HTTP request/response
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = "X-Request-ID"
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3101",
    "https://localhost",
]


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate or generate *X-Request-ID* on every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[type-arg]
        request_id = request.headers.get(_REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers[_REQUEST_ID_HEADER] = request_id

        logger.info(
            "http request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 1),
            },
        )
        return response


def register_middleware(app: FastAPI, *, allowed_origins: list[str] | None = None) -> None:
    """Attach all middleware to a FastAPI *app* instance.

    Call once during application startup before the first request is handled.
    """
    origins = allowed_origins or _ALLOWED_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", _REQUEST_ID_HEADER],
        expose_headers=[_REQUEST_ID_HEADER],
    )

    app.add_middleware(RequestIDMiddleware)
