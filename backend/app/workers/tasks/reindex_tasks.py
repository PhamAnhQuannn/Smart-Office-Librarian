"""Blue-green reindex helpers.

FR-4.3 requires building a candidate namespace in the background and only
atomically swapping the active pointer once validation succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ReindexPointerStore(Protocol):
	"""Abstraction for active namespace pointer persistence."""

	def get_active_namespace(self) -> str:
		...

	def compare_and_swap_namespace(self, *, expected_namespace: str, new_namespace: str) -> bool:
		...


class ReindexValidationError(Exception):
	"""Raised when a candidate index fails validation and swap is blocked."""


class AtomicSwapError(Exception):
	"""Raised when compare-and-swap fails because pointer state changed."""


@dataclass(frozen=True)
class ReindexSwapResult:
	previous_namespace: str
	active_namespace: str
	swapped: bool


class ReindexTaskService:
	"""Coordinates FR-4.3 blue-green namespace swaps."""

	def __init__(self, pointer_store: ReindexPointerStore) -> None:
		self._pointer_store = pointer_store

	def get_query_namespace(self) -> str:
		"""Queries should always resolve through the current active namespace."""
		return self._pointer_store.get_active_namespace()

	def finalize_reindex(self, *, candidate_namespace: str, validation_passed: bool) -> ReindexSwapResult:
		"""Finalizes reindex by atomically switching active namespace on success."""
		current_namespace = self._pointer_store.get_active_namespace()

		if not validation_passed:
			raise ReindexValidationError("candidate namespace failed validation")

		if candidate_namespace == current_namespace:
			return ReindexSwapResult(
				previous_namespace=current_namespace,
				active_namespace=current_namespace,
				swapped=False,
			)

		swapped = self._pointer_store.compare_and_swap_namespace(
			expected_namespace=current_namespace,
			new_namespace=candidate_namespace,
		)
		if not swapped:
			raise AtomicSwapError("active namespace changed before swap could complete")

		return ReindexSwapResult(
			previous_namespace=current_namespace,
			active_namespace=candidate_namespace,
			swapped=True,
		)
