"""Refusal stage for FR-3.3 threshold contract.

Canonical behavior from DECISIONS:
- compare cosine score only
- score >= threshold passes
- score < threshold refuses with LOW_SIMILARITY and top-3 sources
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class RefusalDecision:
	refused: bool
	refusal_reason: Optional[str]
	sources: list[dict[str, Any]]
	primary_cosine_score: float
	threshold: float


class RefusalStage:
	"""Evaluates whether generation should be refused."""

	def run(
		self,
		*,
		primary_cosine_score: float,
		threshold: float,
		ranked_sources: Sequence[dict[str, Any]],
	) -> RefusalDecision:
		if threshold is None:
			raise ValueError("threshold is required")

		top_sources = list(ranked_sources[:3])
		refused = primary_cosine_score < threshold

		return RefusalDecision(
			refused=refused,
			refusal_reason="LOW_SIMILARITY" if refused else None,
			sources=top_sources,
			primary_cosine_score=primary_cosine_score,
			threshold=threshold,
		)
