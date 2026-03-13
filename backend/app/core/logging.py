"""Structured logging helpers with built-in sensitive field redaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REDACTED = "***REDACTED***"
_SENSITIVE_KEYWORDS = (
	"authorization",
	"token",
	"secret",
	"password",
	"api_key",
	"apikey",
	"access_key",
	"private_key",
	"credential",
)


def _is_sensitive_key(key: str) -> bool:
	normalized = key.lower()
	return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def sanitize_log_data(value: Any) -> Any:
	if isinstance(value, dict):
		sanitized: dict[str, Any] = {}
		for key, inner_value in value.items():
			sanitized[key] = REDACTED if _is_sensitive_key(key) else sanitize_log_data(inner_value)
		return sanitized
	if isinstance(value, list):
		return [sanitize_log_data(item) for item in value]
	if isinstance(value, tuple):
		return tuple(sanitize_log_data(item) for item in value)
	return value


@dataclass(frozen=True)
class LogEntry:
	timestamp: str
	event_type: str
	payload: dict[str, Any]


class InMemoryStructuredLogger:
	def __init__(self) -> None:
		self._entries: list[LogEntry] = []

	@property
	def entries(self) -> list[LogEntry]:
		return list(self._entries)

	def emit(self, event_type: str, **payload: Any) -> LogEntry:
		entry = LogEntry(
			timestamp=datetime.now(timezone.utc).isoformat(),
			event_type=event_type,
			payload=sanitize_log_data(payload),
		)
		self._entries.append(entry)
		return entry

	def log_retrieval_failure(
		self,
		*,
		user_id: str,
		query_log_id: str,
		query_text: str,
		reason: str,
		source_count: int,
		request_metadata: dict[str, Any] | None = None,
	) -> LogEntry:
		return self.emit(
			"query.retrieval_failure",
			user_id=user_id,
			query_log_id=query_log_id,
			query_text=query_text,
			reason=reason,
			source_count=source_count,
			request_metadata=request_metadata or {},
		)

	def log_feedback(
		self,
		*,
		user_id: str,
		query_log_id: str,
		vote: str,
		comment: str | None,
		metadata: dict[str, Any] | None = None,
	) -> LogEntry:
		return self.emit(
			"feedback.downvote" if vote == "down" else "feedback.upvote",
			user_id=user_id,
			query_log_id=query_log_id,
			vote=vote,
			comment=comment,
			metadata=metadata or {},
		)
