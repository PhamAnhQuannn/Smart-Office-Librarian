"""Standardised exception hierarchy and FastAPI exception handlers.

All application exceptions derive from AppError so callers can catch the
broad base class when needed.  Each subclass maps to a canonical HTTP status
code and error_code string used by the API error response contract.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    """Resource not found (→ HTTP 404)."""

    status_code = 404
    error_code = "NOT_FOUND"


class ValidationError(AppError):
    """Request payload failed validation (→ HTTP 422)."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class AuthError(AppError):
    """Authentication / authorisation failure (→ HTTP 401/403)."""

    status_code = 401
    error_code = "UNAUTHENTICATED"


class ForbiddenError(AppError):
    """Caller authenticated but lacks required role (→ HTTP 403)."""

    status_code = 403
    error_code = "FORBIDDEN"


class RateLimitError(AppError):
    """Rate-limit exceeded (→ HTTP 429)."""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"

    def __init__(
        self,
        message: str,
        retry_after_seconds: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.retry_after_seconds = retry_after_seconds


class UpstreamError(AppError):
    """Third-party service (OpenAI, Pinecone, GitHub) returned an error."""

    status_code = 502
    error_code = "UPSTREAM_ERROR"


class ConfigurationError(AppError):
    """Required configuration is missing or invalid at startup."""

    status_code = 500
    error_code = "CONFIGURATION_ERROR"


class IndexSafetyError(AppError):
    """Model/index version mismatch detected (FR-4.2)."""

    status_code = 409
    error_code = "INDEX_MISMATCH"


class BudgetExhaustedError(AppError):
    """Monthly token budget exhausted; switch to retrieval-only mode."""

    status_code = 402
    error_code = "BUDGET_EXHAUSTED"
