"""Pydantic schemas for the ingestion API."""
from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    """Input to POST /api/v1/ingest."""

    file_path: str | None = Field(
        default=None,
        description="Absolute path to a local file or directory to ingest.",
    )
    source_url: str | None = Field(
        default=None,
        description="URL of a remote resource to ingest (GitHub repo, blob, etc.).",
    )
    namespace: str = Field(
        default="default",
        description="Target Pinecone namespace.",
    )
    force_reingest: bool = Field(
        default=False,
        description="Re-ingest even if the source fingerprint is unchanged.",
    )


class IngestResponse(BaseModel):
    """Immediate response to an ingest request."""

    run_id: str = Field(description="Unique identifier for the queued ingest run.")
    status: str = Field(description="\"queued\" | \"running\" | \"completed\" | \"failed\"")
    namespace: str
    message: str = ""


class IngestRunStatus(BaseModel):
    """Detailed status of a single ingest run."""

    run_id: str
    namespace: str
    status: str
    chunks_created: int = 0
    chunks_skipped: int = 0
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
