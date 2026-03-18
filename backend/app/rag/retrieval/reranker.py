"""Score-based reranker.

For MVP this is a lightweight cosine-score pass-through reranker.
Results already arrive sorted by the vector store; this class applies
an optional score floor and returns the top-k.
"""

from __future__ import annotations

from typing import Any


class Reranker:
    """Applies a score floor and returns top-k ranked sources."""

    def __init__(self, *, score_floor: float = 0.0, top_k: int = 5) -> None:
        self._score_floor = score_floor
        self._top_k = top_k

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        *,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Filter by score floor and return top_k results."""
        limit = top_k if top_k is not None else self._top_k
        filtered = [
            c for c in candidates if c.get("score", 0.0) >= self._score_floor
        ]
        return filtered[:limit]
