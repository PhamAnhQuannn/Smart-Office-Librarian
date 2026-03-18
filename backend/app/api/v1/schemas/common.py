"""Shared Pydantic response/request schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard JSON error envelope."""

    error: str = Field(description="Machine-readable error code or short message.")
    detail: str | None = Field(default=None, description="Human-readable detail.")
    request_id: str | None = Field(default=None, description="X-Request-ID echo.")


class PaginationMeta(BaseModel):
    """Pagination metadata appended to list responses."""

    page: int = Field(ge=1, description="1-based page number.")
    page_size: int = Field(ge=1, le=200, description="Items per page.")
    total: int = Field(ge=0, description="Total number of items across all pages.")
    has_next: bool = Field(description="Whether a subsequent page exists.")


class HealthStatus(BaseModel):
    status: str
    checks: dict[str, bool] | None = None
