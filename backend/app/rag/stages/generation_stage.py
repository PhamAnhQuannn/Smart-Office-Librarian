"""Generation stage: prompt → LLM → citations → confidence.

Contract:
  Input:  query_text, ranked_sources, namespace
  Output: dict with token_events, sources (citations), confidence,
          prompt_tokens, completion_tokens
"""

from __future__ import annotations

from typing import Any

from app.rag.generation.citation_mapper import map_citations
from app.rag.generation.confidence_calculator import score_to_confidence


class GenerationStage:
    """Orchestrates LLM answer generation and citation mapping."""

    def __init__(self, *, answer_generator: Any) -> None:
        self._generator = answer_generator

    def run(
        self,
        *,
        query_text: str,
        ranked_sources: list[dict[str, Any]],
        namespace: str,
    ) -> dict[str, Any]:
        gen_result = self._generator.generate(
            query_text=query_text,
            sources=ranked_sources,
        )

        citations = map_citations(ranked_sources)
        primary_score = ranked_sources[0]["score"] if ranked_sources else 0.0
        confidence = score_to_confidence(primary_score)

        return {
            "token_events": gen_result["token_events"],
            "sources": citations,
            "confidence": confidence,
            "prompt_tokens": gen_result.get("prompt_tokens", 0),
            "completion_tokens": gen_result.get("completion_tokens", 0),
        }
