"""Unit tests for Reranker and generation sub-components."""
from __future__ import annotations

import pytest

from app.rag.retrieval.reranker import Reranker
from app.rag.generation.confidence_calculator import score_to_confidence
from app.rag.generation.citation_mapper import map_citations
from app.rag.generation.prompt_builder import build_messages


# ---------------------------------------------------------------------------
# Reranker
# ---------------------------------------------------------------------------

class TestReranker:
    def _candidates(self, scores: list[float]) -> list[dict]:
        return [{"id": str(i), "score": s, "text": f"chunk {i}"} for i, s in enumerate(scores)]

    def test_returns_top_k(self) -> None:
        r = Reranker(score_floor=0.0, top_k=3)
        candidates = self._candidates([0.9, 0.8, 0.7, 0.6, 0.5])
        result = r.rerank(candidates)
        assert len(result) == 3

    def test_filters_below_floor(self) -> None:
        r = Reranker(score_floor=0.75, top_k=10)
        candidates = self._candidates([0.9, 0.8, 0.6, 0.4])
        result = r.rerank(candidates)
        assert all(c["score"] >= 0.75 for c in result)
        assert len(result) == 2

    def test_empty_input(self) -> None:
        r = Reranker()
        assert r.rerank([]) == []

    def test_override_top_k_at_call_time(self) -> None:
        r = Reranker(score_floor=0.0, top_k=5)
        candidates = self._candidates([0.9, 0.8, 0.7, 0.6, 0.5])
        result = r.rerank(candidates, top_k=2)
        assert len(result) == 2

    def test_all_below_floor_returns_empty(self) -> None:
        r = Reranker(score_floor=0.99, top_k=5)
        candidates = self._candidates([0.5, 0.4, 0.3])
        assert r.rerank(candidates) == []

    def test_candidates_missing_score_default_zero(self) -> None:
        r = Reranker(score_floor=0.5, top_k=5)
        candidates = [{"id": "1", "text": "no score field"}]
        # Candidates without 'score' key should be treated as 0.0 → filtered out
        assert r.rerank(candidates) == []


# ---------------------------------------------------------------------------
# ConfidenceCalculator
# ---------------------------------------------------------------------------

class TestConfidenceCalculator:
    def test_high_confidence(self) -> None:
        assert score_to_confidence(0.95) == "HIGH"
        assert score_to_confidence(0.85) == "HIGH"

    def test_medium_confidence(self) -> None:
        assert score_to_confidence(0.80) == "MEDIUM"
        assert score_to_confidence(0.70) == "MEDIUM"

    def test_low_confidence(self) -> None:
        assert score_to_confidence(0.69) == "LOW"
        assert score_to_confidence(0.0) == "LOW"

    def test_exact_boundary_high(self) -> None:
        # 0.85 is the boundary for HIGH
        assert score_to_confidence(0.85) == "HIGH"

    def test_exact_boundary_medium(self) -> None:
        # 0.70 is the boundary for MEDIUM
        assert score_to_confidence(0.70) == "MEDIUM"


# ---------------------------------------------------------------------------
# CitationMapper
# ---------------------------------------------------------------------------

class TestCitationMapper:
    def _sources(self, n: int) -> list[dict]:
        return [
            {
                "file_path": f"/docs/file{i}.md",
                "source_url": f"https://example.com/file{i}",
                "start_line": i * 10 + 1,
                "end_line": i * 10 + 10,
                "text": f"Chunk text {i}",
                "score": 0.9 - i * 0.05,
            }
            for i in range(n)
        ]

    def test_returns_top_3(self) -> None:
        sources = self._sources(5)
        citations = map_citations(sources)
        assert len(citations) <= 3

    def test_empty_sources(self) -> None:
        assert map_citations([]) == []

    def test_citation_has_required_keys(self) -> None:
        citations = map_citations(self._sources(2))
        for c in citations:
            assert "file_path" in c
            assert "start_line" in c
            assert "end_line" in c

    def test_single_source(self) -> None:
        citations = map_citations(self._sources(1))
        assert len(citations) == 1


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    def _sources(self) -> list[dict]:
        return [
            {
                "file_path": "/docs/guide.md",
                "text": "RAG stands for Retrieval Augmented Generation.",
                "source_url": None,
                "start_line": 1,
                "end_line": 5,
                "score": 0.9,
            }
        ]

    def test_returns_list_of_dicts(self) -> None:
        messages = build_messages("What is RAG?", self._sources())
        assert isinstance(messages, list)
        assert all("role" in m and "content" in m for m in messages)

    def test_contains_system_and_user(self) -> None:
        messages = build_messages("What is RAG?", self._sources())
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles

    def test_query_in_user_message(self) -> None:
        messages = build_messages("What is embedlyzer?", self._sources())
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        assert "embedlyzer" in user_msg.lower()

    def test_empty_sources_still_works(self) -> None:
        messages = build_messages("A question", [])
        assert len(messages) >= 2
