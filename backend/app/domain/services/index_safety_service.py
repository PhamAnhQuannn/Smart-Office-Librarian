"""Domain service for cross-version index safety checks.

FR-4.2 requires preventing queries against incompatible model/index versions.
This service raises canonical mismatch errors that can be mapped to HTTP 409.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class IndexSafetyMismatch:
	error_code: str
	message: str
	expected_model_id: str
	expected_index_version: int
	received_model_id: str
	received_index_version: int

	def to_error_payload(self) -> dict[str, Any]:
		return {
			"error_code": self.error_code,
			"message": self.message,
			"details": {
				"expected_model_id": self.expected_model_id,
				"expected_index_version": self.expected_index_version,
				"received_model_id": self.received_model_id,
				"received_index_version": self.received_index_version,
			},
		}


class IndexSafetyMismatchError(Exception):
	def __init__(self, mismatch: IndexSafetyMismatch) -> None:
		super().__init__(mismatch.message)
		self.mismatch = mismatch

	@property
	def error_code(self) -> str:
		return self.mismatch.error_code

	def to_error_payload(self) -> dict[str, Any]:
		return self.mismatch.to_error_payload()


class IndexSafetyService:
	"""Validates query model/index compatibility against active index metadata."""

	def build_vector_metadata(
		self,
		*,
		model_id: str,
		index_version: int,
		base_metadata: Mapping[str, Any] | None = None,
	) -> dict[str, Any]:
		"""Builds canonical vector metadata with required version tags.

		FR-4.1 requires every stored vector to include `model_id` and
		`index_version` so query-time compatibility checks are deterministic.
		"""
		if not model_id:
			raise ValueError("model_id is required")
		if index_version is None or index_version < 1:
			raise ValueError("index_version must be >= 1")

		metadata = dict(base_metadata or {})
		metadata["model_id"] = model_id
		metadata["index_version"] = index_version
		return metadata

	def ensure_vector_metadata_tags(self, metadata: Mapping[str, Any]) -> None:
		"""Validates required FR-4.1 metadata tags before vector persistence."""
		if metadata.get("model_id") in (None, ""):
			raise ValueError("vector metadata missing model_id")
		if metadata.get("index_version") is None:
			raise ValueError("vector metadata missing index_version")

	def ensure_compatible(
		self,
		*,
		expected_model_id: str,
		expected_index_version: int,
		received_model_id: str,
		received_index_version: int,
	) -> None:
		if expected_model_id is None or expected_index_version is None:
			raise ValueError("expected index metadata is required")
		if received_model_id is None or received_index_version is None:
			raise ValueError("received query metadata is required")

		if expected_model_id != received_model_id:
			raise IndexSafetyMismatchError(
				IndexSafetyMismatch(
					error_code="EMBEDDING_MODEL_MISMATCH",
					message="Index safety mismatch",
					expected_model_id=expected_model_id,
					expected_index_version=expected_index_version,
					received_model_id=received_model_id,
					received_index_version=received_index_version,
				)
			)

		if expected_index_version != received_index_version:
			raise IndexSafetyMismatchError(
				IndexSafetyMismatch(
					error_code="INDEX_VERSION_MISMATCH",
					message="Index safety mismatch",
					expected_model_id=expected_model_id,
					expected_index_version=expected_index_version,
					received_model_id=received_model_id,
					received_index_version=received_index_version,
				)
			)
