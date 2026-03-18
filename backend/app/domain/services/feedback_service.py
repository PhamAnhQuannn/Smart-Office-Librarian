"""Feedback service: persist and query thumbs-up/down votes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FeedbackRecord:
    query_log_id: str
    user_id: str
    vote: str  # 'up' | 'down'
    comment: str | None = None


class FeedbackService:
    """Records and retrieves user feedback on query results."""

    def __init__(self, feedback_repo: Any | None = None) -> None:
        self._repo = feedback_repo

    def record_feedback(
        self,
        *,
        query_log_id: str,
        user_id: str,
        vote: str,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a feedback vote.  Falls back to no-op when repo is absent."""
        if vote not in ("up", "down"):
            raise ValueError("vote must be 'up' or 'down'")

        if self._repo is not None and hasattr(self._repo, "create"):
            self._repo.create(
                query_log_id=query_log_id,
                user_id=user_id,
                vote=vote,
                comment=comment,
                metadata=metadata or {},
            )

        return {
            "query_log_id": query_log_id,
            "user_id": user_id,
            "vote": vote,
            "stored": self._repo is not None,
        }

    def list_for_query_log(self, query_log_id: str) -> list[dict[str, Any]]:
        """Return all feedback for a given query log entry."""
        if self._repo is None or not hasattr(self._repo, "list_by_query_log"):
            return []
        records = self._repo.list_by_query_log(query_log_id)
        return [
            {
                "id": str(getattr(r, "id", "")),
                "vote": getattr(r, "vote", ""),
                "comment": getattr(r, "comment", None),
            }
            for r in records
        ]
