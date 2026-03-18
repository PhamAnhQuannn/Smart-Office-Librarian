"""Pydantic schemas for the query API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Input to POST /api/v1/query."""

    query_text: str = Field(min_length=1, max_length=1000, description="The question to answer.")
    namespace: str = Field(default="default", description="Pinecone namespace to search.")
    threshold_override: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override the namespace's configured similarity threshold for this request.",
    )
    stream: bool = Field(default=True, description="Whether to stream the response via SSE.")


class SourceCitation(BaseModel):
    """A single cited source chunk in a query response."""

    file_path: str | None = None
    source_url: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    text: str
    score: float


class QueryResponse(BaseModel):
    """Final SSE payload for a completed query."""

    query_log_id: str
    mode: str = Field(description="\"answer\" | \"refusal\" | \"retrieval_only\".")
    answer_text: str | None = None
    confidence: str | None = Field(default=None, description="HIGH | MEDIUM | LOW")
    refusal_reason: str | None = None
    sources: list[SourceCitation] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
