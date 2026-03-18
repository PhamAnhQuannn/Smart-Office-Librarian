"""Data contracts for the generation stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GenerationRequest:
    query_text: str
    ranked_sources: list[dict[str, Any]]
    namespace: str
    max_tokens: int = 1024


@dataclass
class GenerationResult:
    token_events: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence: str = "LOW"
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "token_events": self.token_events,
            "sources": self.sources,
            "confidence": self.confidence,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }
