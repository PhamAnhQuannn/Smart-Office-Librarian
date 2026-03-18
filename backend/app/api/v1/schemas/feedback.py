"""Pydantic schemas for the feedback API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """Input to POST /api/v1/feedback."""

    query_log_id: str = Field(description="ID of the query log entry being rated.")
    vote: str = Field(
        description="\"up\" to signal a helpful response, \"down\" for an unhelpful one.",
        pattern=r"^(up|down)$",
    )
    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text comment.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata attached by the client.",
    )


class FeedbackResponse(BaseModel):
    """Response after recording feedback."""

    ok: bool = True
    feedback_id: str | None = None
