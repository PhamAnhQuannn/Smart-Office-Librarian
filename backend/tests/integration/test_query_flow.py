from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from app.domain.services.query_service import QueryRequest, QueryService
from app.rag.stages.refusal_stage import RefusalStage


def _sources(count: int) -> list[dict[str, Any]]:
	return [
		{
			"file_path": f"docs/file_{i}.md",
			"source_url": f"https://example.com/file_{i}.md",
			"start_line": i,
			"end_line": i + 10,
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


class _IntegratedPipeline:
	def __init__(self, *, primary_score: float, ranked_sources: list[dict[str, Any]]) -> None:
		self._primary_score = primary_score
		self._ranked_sources = ranked_sources
		self._refusal_stage = RefusalStage()
		self.generation_called = False

	def run(
		self,
		*,
		query_text: str,
		rbac_filter: dict[str, Any] | None,
		namespace: str,
		retrieval_only_mode: bool,
		threshold: float,
	) -> dict[str, Any]:
		if retrieval_only_mode:
			return {
				"mode": "retrieval_only",
				"refusal_reason": "BUDGET_EXCEEDED",
				"sources": self._ranked_sources[:3],
				"token_events": [],
				"threshold": threshold,
			}

		decision = self._refusal_stage.run(
			primary_cosine_score=self._primary_score,
			threshold=threshold,
			ranked_sources=self._ranked_sources,
		)
		if decision.refused:
			return {
				"mode": "refusal",
				"refusal_reason": decision.refusal_reason,
				"sources": decision.sources,
				"token_events": [],
				"threshold": decision.threshold,
			}

		self.generation_called = True
		return {
			"mode": "answer",
			"refusal_reason": None,
			"sources": decision.sources,
			"token_events": ["answer token"],
			"threshold": decision.threshold,
			"query_text": query_text,
			"rbac_filter": rbac_filter,
			"namespace": namespace,
		}


def test_query_flow_refusal_contract_with_injected_threshold() -> None:
	threshold_service = _FakeThresholdService(value=0.65)
	pipeline = _IntegratedPipeline(primary_score=0.40, ranked_sources=_sources(5))
	service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

	result = service.execute(
		QueryRequest(
			query_text="confidential policy",
			namespace="dev",
			index_version=1,
			rbac_filter={"visibility": "private"},
		)
	)

	assert threshold_service.calls == [("dev", 1)]
	assert result["mode"] == "refusal"
	assert result["refusal_reason"] == "LOW_SIMILARITY"
	assert len(result["sources"]) == 3
	assert result["token_events"] == []
	assert result["threshold"] == 0.65
	assert {
		"file_path",
		"source_url",
		"start_line",
		"end_line",
		"text",
	}.issubset(result["sources"][0].keys())


def test_query_flow_retrieval_only_mode_skips_generation() -> None:
	threshold_service = _FakeThresholdService(value=0.65)
	pipeline = _IntegratedPipeline(primary_score=0.99, ranked_sources=_sources(4))
	service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

	result = service.execute(
		QueryRequest(
			query_text="budget pressure",
			namespace="staging",
			index_version=1,
			retrieval_only_mode=True,
		)
	)

	assert result["mode"] == "retrieval_only"
	assert result["refusal_reason"] in {"BUDGET_EXCEEDED", "LLM_UNAVAILABLE"}
	assert result["token_events"] == []
	assert pipeline.generation_called is False


def test_query_flow_equal_threshold_allows_answer() -> None:
	threshold_service = _FakeThresholdService(value=0.65)
	pipeline = _IntegratedPipeline(primary_score=0.65, ranked_sources=_sources(3))
	service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

	result = service.execute(
		QueryRequest(
			query_text="where is onboarding guide",
			namespace="prod",
			index_version=1,
		)
	)

	assert result["mode"] == "answer"
	assert result["refusal_reason"] is None
	assert result["token_events"] == ["answer token"]
	assert result["threshold"] == 0.65
