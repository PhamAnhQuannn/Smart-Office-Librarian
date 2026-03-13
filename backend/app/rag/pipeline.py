"""RAG pipeline orchestration.

Step 18 focuses on FR-3 integration behavior:
- threshold is injected by Domain and used by refusal stage
- refusal mode short-circuits generation
- retrieval-only mode skips generation and returns sources
"""

from __future__ import annotations

from typing import Any


class RAGPipeline:
	"""Coordinates retrieval, refusal, and generation stages."""

	def __init__(
		self,
		*,
		retrieval_stage: Any,
		refusal_stage: Any,
		generation_stage: Any,
		retrieval_only_reason: str = "BUDGET_EXCEEDED",
	) -> None:
		self._retrieval_stage = retrieval_stage
		self._refusal_stage = refusal_stage
		self._generation_stage = generation_stage
		self._retrieval_only_reason = retrieval_only_reason

	def run(
		self,
		*,
		query_text: str,
		rbac_filter: dict[str, Any] | None,
		namespace: str,
		retrieval_only_mode: bool,
		threshold: float,
	) -> dict[str, Any]:
		retrieval_result = self._retrieval_stage.run(
			query_text=query_text,
			rbac_filter=rbac_filter,
			namespace=namespace,
		)

		ranked_sources = list(retrieval_result.get("ranked_sources", []))
		primary_score = retrieval_result.get("primary_cosine_score")
		if primary_score is None:
			primary_score = 0.0

		retrieval_cache_hit = bool(retrieval_result.get("cache_hit", False))
		retrieval_latency_ms = retrieval_result.get("latency_ms")

		if retrieval_only_mode:
			return {
				"mode": "retrieval_only",
				"refusal_reason": self._retrieval_only_reason,
				"sources": ranked_sources[:3],
				"token_events": [],
				"threshold": threshold,
				"retrieval_cache_hit": retrieval_cache_hit,
				"retrieval_latency_ms": retrieval_latency_ms,
			}

		decision = self._refusal_stage.run(
			primary_cosine_score=float(primary_score),
			threshold=threshold,
			ranked_sources=ranked_sources,
		)
		if decision.refused:
			return {
				"mode": "refusal",
				"refusal_reason": decision.refusal_reason,
				"sources": decision.sources,
				"token_events": [],
				"threshold": decision.threshold,
				"retrieval_cache_hit": retrieval_cache_hit,
				"retrieval_latency_ms": retrieval_latency_ms,
			}

		generation_result = self._generation_stage.run(
			query_text=query_text,
			ranked_sources=ranked_sources,
			namespace=namespace,
		)
		return {
			"mode": "answer",
			"refusal_reason": None,
			"sources": generation_result.get("sources", decision.sources),
			"token_events": generation_result.get("token_events", []),
			"threshold": decision.threshold,
			"retrieval_cache_hit": retrieval_cache_hit,
			"retrieval_latency_ms": retrieval_latency_ms,
		}
