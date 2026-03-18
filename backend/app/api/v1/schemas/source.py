"""Pydantic schemas for the source management API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SourceRecord(BaseModel):
    """A single indexed source as returned by GET /api/v1/admin/sources."""

    source_id: str
    file_path: str | None = None
    source_url: str | None = None
    namespace: str
    chunk_count: int = 0
    created_at: str | None = None
    last_ingested_at: str | None = None


class SourceListResponse(BaseModel):
    """Paginated list of indexed sources."""

    sources: list[SourceRecord] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class DeleteSourceResponse(BaseModel):
    """Response after a DELETE /api/v1/admin/sources/{source_id} request."""

    ok: bool = True
    source_id: str
    message: str = ""
