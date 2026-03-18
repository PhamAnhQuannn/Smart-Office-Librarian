"""Data contracts for the retrieval stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RetrievalRequest:
    query_text: str
    namespace: str
    rbac_filter: dict[str, Any] | None = None
    top_k: int = 10


@dataclass(frozen=True)
class RetrievedChunk:
    vector_id: str
    text: str
    score: float
    file_path: str
    source_url: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    namespace: str = "dev"


@dataclass
class RetrievalResult:
    ranked_sources: list[RetrievedChunk] = field(default_factory=list)
    primary_cosine_score: float = 0.0
    cache_hit: bool = False
    latency_ms: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ranked_sources": [
                {
                    "vector_id": c.vector_id,
                    "text": c.text,
                    "score": c.score,
                    "file_path": c.file_path,
                    "source_url": c.source_url,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "namespace": c.namespace,
                }
                for c in self.ranked_sources
            ],
            "primary_cosine_score": self.primary_cosine_score,
            "cache_hit": self.cache_hit,
            "latency_ms": self.latency_ms,
        }
