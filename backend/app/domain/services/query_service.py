"""Domain query orchestration service.

This service is intentionally lightweight for Step 04 and focuses on
FR-3.3 threshold handling: fetch threshold in Domain and pass it into the
pipeline for refusal logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class QueryRequest:
	query_text: str
	namespace: str
	index_version: int
	rbac_filter: Optional[dict[str, Any]] = None
	retrieval_only_mode: bool = False


class QueryService:
	"""Orchestrates threshold retrieval and pipeline execution."""

	def __init__(self, pipeline: Any, threshold_service: Any) -> None:
		self._pipeline = pipeline
		self._threshold_service = threshold_service

	def execute(self, request: QueryRequest) -> Any:
		threshold = self._threshold_service.get_threshold(
			namespace=request.namespace,
			index_version=request.index_version,
		)

		return self._pipeline.run(
			query_text=request.query_text,
			rbac_filter=request.rbac_filter,
			namespace=request.namespace,
			retrieval_only_mode=request.retrieval_only_mode,
			threshold=threshold,
		)
