from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.services.query_service import QueryRequest, QueryService
from app.rag.pipeline import RAGPipeline
from app.rag.stages.refusal_stage import RefusalStage


def _sources(count: int) -> list[dict[str, Any]]:
    return [
        {
            "file_path": f"docs/file_{i}.md",
            "source_url": f"https://example.com/file_{i}.md",
            "start_line": i,
            "end_line": i + 5,
            "text": f"snippet {i}",
        }
        for i in range(1, count + 1)
    ]


class _FakeThresholdService:
    def __init__(self, value: float) -> None:
        self.value = value
        self.calls: list[tuple[str, int]] = []

    def get_threshold(self, *, namespace: str, index_version: int) -> float:
        self.calls.append((namespace, index_version))
        return self.value


class _FakeRetrievalStage:
    def __init__(
        self,
        *,
        primary_score: float,
        ranked_sources: list[dict[str, Any]],
        cache_hit: bool = False,
        latency_ms: int = 0,
    ) -> None:
        self._primary_score = primary_score
        self._ranked_sources = ranked_sources
        self._cache_hit = cache_hit
        self._latency_ms = latency_ms
        self.calls: list[dict[str, Any]] = []

    def run(self, *, query_text: str, rbac_filter: dict[str, Any] | None, namespace: str) -> dict[str, Any]:
        self.calls.append(
            {
                "query_text": query_text,
                "rbac_filter": rbac_filter,
                "namespace": namespace,
            }
        )
        return {
            "primary_cosine_score": self._primary_score,
            "ranked_sources": self._ranked_sources,
            "cache_hit": self._cache_hit,
            "latency_ms": self._latency_ms,
        }


class _FakeGenerationStage:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, *, query_text: str, ranked_sources: list[dict[str, Any]], namespace: str) -> dict[str, Any]:
        self.calls.append(
            {
                "query_text": query_text,
                "ranked_sources": ranked_sources,
                "namespace": namespace,
            }
        )
        return {
            "token_events": ["generated token"],
            "sources": ranked_sources[:3],
        }


def test_rag_pipeline_threshold_injected_from_domain() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    retrieval_stage = _FakeRetrievalStage(primary_score=0.80, ranked_sources=_sources(5))
    generation_stage = _FakeGenerationStage()
    pipeline = RAGPipeline(
        retrieval_stage=retrieval_stage,
        refusal_stage=RefusalStage(),
        generation_stage=generation_stage,
    )
    service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

    result = service.execute(
        QueryRequest(
            query_text="how to onboard",
            namespace="dev",
            index_version=1,
            rbac_filter={"visibility": "private"},
        )
    )

    assert threshold_service.calls == [("dev", 1)]
    assert result["mode"] == "answer"
    assert result["threshold"] == 0.65
    assert result["token_events"] == ["generated token"]
    assert retrieval_stage.calls[0]["rbac_filter"] == {"visibility": "private"}
    assert len(generation_stage.calls) == 1


def test_rag_pipeline_refusal_flow_when_score_below_threshold() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    retrieval_stage = _FakeRetrievalStage(primary_score=0.40, ranked_sources=_sources(6))
    generation_stage = _FakeGenerationStage()
    pipeline = RAGPipeline(
        retrieval_stage=retrieval_stage,
        refusal_stage=RefusalStage(),
        generation_stage=generation_stage,
    )
    service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

    result = service.execute(
        QueryRequest(
            query_text="confidential architecture",
            namespace="staging",
            index_version=1,
        )
    )

    assert result["mode"] == "refusal"
    assert result["refusal_reason"] == "LOW_SIMILARITY"
    assert result["token_events"] == []
    assert len(result["sources"]) == 3
    assert len(generation_stage.calls) == 0


def test_rag_pipeline_cache_hit_is_faster_than_miss() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    hit_pipeline = RAGPipeline(
        retrieval_stage=_FakeRetrievalStage(
            primary_score=0.9,
            ranked_sources=_sources(3),
            cache_hit=True,
            latency_ms=30,
        ),
        refusal_stage=RefusalStage(),
        generation_stage=_FakeGenerationStage(),
    )
    miss_pipeline = RAGPipeline(
        retrieval_stage=_FakeRetrievalStage(
            primary_score=0.9,
            ranked_sources=_sources(3),
            cache_hit=False,
            latency_ms=180,
        ),
        refusal_stage=RefusalStage(),
        generation_stage=_FakeGenerationStage(),
    )

    hit_result = QueryService(pipeline=hit_pipeline, threshold_service=threshold_service).execute(
        QueryRequest(query_text="cached", namespace="dev", index_version=1)
    )
    miss_result = QueryService(pipeline=miss_pipeline, threshold_service=threshold_service).execute(
        QueryRequest(query_text="uncached", namespace="dev", index_version=1)
    )

    assert hit_result["retrieval_cache_hit"] is True
    assert miss_result["retrieval_cache_hit"] is False
    assert hit_result["retrieval_latency_ms"] < miss_result["retrieval_latency_ms"]


def test_rag_pipeline_retrieval_only_mode_skips_generation() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    retrieval_stage = _FakeRetrievalStage(
        primary_score=0.95,
        ranked_sources=_sources(4),
        cache_hit=True,
        latency_ms=35,
    )
    generation_stage = _FakeGenerationStage()
    pipeline = RAGPipeline(
        retrieval_stage=retrieval_stage,
        refusal_stage=RefusalStage(),
        generation_stage=generation_stage,
    )
    service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

    rbac_filter = {"visibility": "private", "allowed_user_ids": {"$in": ["user-1"]}}
    result = service.execute(
        QueryRequest(
            query_text="budget fallback",
            namespace="prod",
            index_version=1,
            retrieval_only_mode=True,
            rbac_filter=rbac_filter,
        )
    )

    assert result["mode"] == "retrieval_only"
    assert result["refusal_reason"] in {"BUDGET_EXCEEDED", "LLM_UNAVAILABLE"}
    assert result["token_events"] == []
    assert len(result["sources"]) == 3
    assert result["retrieval_cache_hit"] is True
    assert result["retrieval_latency_ms"] == 35
    assert retrieval_stage.calls[0]["rbac_filter"] == rbac_filter
    assert len(generation_stage.calls) == 0
