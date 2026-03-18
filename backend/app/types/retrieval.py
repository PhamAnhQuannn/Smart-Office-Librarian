"""Retrieval-related types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalHit:
    vector_id: str
    score: float
    namespace: str
    text: str
    file_path: str | None = None
    source_url: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    hits: list[RetrievalHit] = field(default_factory=list)
    query_text: str = ""
    namespace: str = "dev"
    threshold_used: float = 0.75

    @property
    def top_score(self) -> float:
        return self.hits[0].score if self.hits else 0.0

    @property
    def passed_threshold(self) -> bool:
        return self.top_score >= self.threshold_used
