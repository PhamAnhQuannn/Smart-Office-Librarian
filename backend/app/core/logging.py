"""Structured logging helpers with built-in sensitive field redaction."""

from __future__ import annotations

import re
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
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-+/=]+")
_JWT_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}\b")
_PROVIDER_TOKEN_PATTERN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,})\b")


def _is_sensitive_key(key: str) -> bool:
	normalized = key.lower()
	return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def _sanitize_text(value: str) -> str:
	redacted = _BEARER_TOKEN_PATTERN.sub("Bearer ***REDACTED***", value)
	redacted = _JWT_PATTERN.sub(REDACTED, redacted)
	redacted = _PROVIDER_TOKEN_PATTERN.sub(REDACTED, redacted)
	return redacted


def sanitize_log_data(value: Any) -> Any:
	if isinstance(value, dict):
		sanitized: dict[str, Any] = {}
		for key, inner_value in value.items():
			sanitized[key] = REDACTED if _is_sensitive_key(key) else sanitize_log_data(inner_value)
		return sanitized
	if isinstance(value, str):
		return _sanitize_text(value)
	if isinstance(value, list):
		return [sanitize_log_data(item) for item in value]
	if isinstance(value, tuple):
		return tuple(sanitize_log_data(item) for item in value)
	return value


def safe_error_message(message: str) -> str:
	"""Redact credentials/tokens before exposing messages externally."""
	return _sanitize_text(message)


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
