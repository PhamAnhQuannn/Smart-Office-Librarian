"""Domain service for cross-version index safety checks.

FR-4.2 requires preventing queries against incompatible model/index versions.
This service raises canonical mismatch errors that can be mapped to HTTP 409.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
