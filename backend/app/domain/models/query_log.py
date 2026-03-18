"""Domain model: QueryLog."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class QueryLog:
    id: str
    user_id: str | None
    query_text: str
    mode: str  # "answer" | "refusal" | "retrieval_only"
    namespace: str = "dev"
    index_version: int = 1
    refusal_reason: str | None = None
    confidence: str | None = None  # "HIGH" | "MEDIUM" | "LOW"
    primary_cosine_score: float | None = None
    threshold: float | None = None
    latency_ms: float | None = None
    ttft_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    sources: dict[str, Any] | None = None
    created_at: datetime | None = None
