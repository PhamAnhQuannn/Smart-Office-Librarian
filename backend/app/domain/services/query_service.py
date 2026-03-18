"""Domain query orchestration service.

This service is intentionally lightweight for Step 04 and focuses on
FR-3.3 threshold handling: fetch threshold in Domain and pass it into the
pipeline for refusal logic.

Step 11 adds FR-4.2 support by optionally validating query model/index
compatibility before pipeline execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class QueryRequest:
	query_text: str
	namespace: str
	index_version: int
	model_id: str = "text-embedding-3-small-v1"
	rbac_filter: Optional[dict[str, Any]] = None
	retrieval_only_mode: bool = False


class QueryService:
	"""Orchestrates safety check, threshold retrieval, and pipeline execution."""

	def __init__(
		self,
		pipeline: Any,
		threshold_service: Any,
		index_safety_service: Any | None = None,
		index_metadata_provider: Any | None = None,
	) -> None:
		self._pipeline = pipeline
		self._threshold_service = threshold_service
		self._index_safety_service = index_safety_service
		self._index_metadata_provider = index_metadata_provider

	def _validate_index_safety(self, request: QueryRequest) -> None:
		if self._index_safety_service is None or self._index_metadata_provider is None:
			return

		metadata = self._index_metadata_provider.get_index_metadata(namespace=request.namespace)
		self._index_safety_service.ensure_compatible(
			expected_model_id=metadata["model_id"],
			expected_index_version=metadata["index_version"],
			received_model_id=request.model_id,
			received_index_version=request.index_version,
		)

	def execute(self, request: QueryRequest) -> Any:
		# Validate that the query text is non-empty before any pipeline call
		if not request.query_text or not request.query_text.strip():
			from app.core.errors import ValidationError
			raise ValidationError("query_text must not be blank")

		self._validate_index_safety(request)

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
