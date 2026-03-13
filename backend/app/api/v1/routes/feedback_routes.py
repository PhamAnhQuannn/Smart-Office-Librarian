"""FR-5.3 feedback route helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logging import InMemoryStructuredLogger
from app.core.metrics import FEEDBACK_TOTAL, InMemoryMetricsRegistry
from app.core.security import AuthenticatedUser

_VALID_VOTES = {"up", "down"}


@dataclass(frozen=True)
class FeedbackSubmission:
	query_log_id: str
	vote: str
	comment: str | None = None
	metadata: dict[str, Any] | None = None


def submit_feedback(
	submission: FeedbackSubmission,
	*,
	user: AuthenticatedUser,
	logger: InMemoryStructuredLogger,
	metrics: InMemoryMetricsRegistry,
) -> dict[str, Any]:
	if submission.vote not in _VALID_VOTES:
		raise ValueError("Feedback vote must be 'up' or 'down'")

	metrics.increment(FEEDBACK_TOTAL, vote=submission.vote)
	if submission.vote == "down":
		logger.log_feedback(
			user_id=user.user_id,
			query_log_id=submission.query_log_id,
			vote=submission.vote,
			comment=submission.comment,
			metadata=submission.metadata,
		)

	return {
		"status_code": 202,
		"headers": {"Content-Type": "application/json"},
		"body": {
			"status": "accepted",
			"query_log_id": submission.query_log_id,
			"vote": submission.vote,
			"review_required": submission.vote == "down",
		},
	}
