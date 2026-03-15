"""Structured logging helpers with built-in sensitive field redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

REDACTED = "***REDACTED***"
AUDIT_LOG_RETENTION_DAYS = 14
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
_SENSITIVE_HEADER_KEYWORDS = (
	"authorization",
	"api-key",
	"api_key",
	"token",
	"secret",
	"cookie",
)
_HEADER_CONTAINER_KEYS = {"headers", "request_headers", "response_headers"}
_FILE_CONTENT_FIELD_KEYS = {"file_content", "full_file_content", "raw_file_content"}
_PII_REDACTION_FIELD_KEYWORDS = ("prompt", "query", "question")
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-+/=]+")
_JWT_PATTERN = re.compile(r"\b[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}\.[A-Za-z0-9_-]{3,}\b")
_PROVIDER_TOKEN_PATTERN = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,})\b")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,2}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b")
_SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_AUDIT_RESOURCE_TYPES = {"source", "threshold", "role"}
_AUDIT_ACTIONS = {"created", "updated", "deleted", "assigned"}
_AUDIT_MAX_CHANGES = 20
_AUDIT_MAX_COLLECTION_ITEMS = 10
_AUDIT_MAX_KEY_LENGTH = 64
_AUDIT_MAX_TEXT_LENGTH = 256
_AUDIT_ELLIPSIS = "..."


def _trim_audit_text(value: str, *, max_length: int = _AUDIT_MAX_TEXT_LENGTH) -> str:
	if len(value) <= max_length:
		return value
	trim_length = max(0, max_length - len(_AUDIT_ELLIPSIS))
	return value[:trim_length] + _AUDIT_ELLIPSIS


def _bound_audit_value(value: Any, *, depth: int = 0) -> Any:
	if isinstance(value, str):
		return _trim_audit_text(value)
	if isinstance(value, (int, float, bool)) or value is None:
		return value

	if depth >= 2:
		return _trim_audit_text(str(value))

	if isinstance(value, dict):
		bounded: dict[str, Any] = {}
		for index, (key, inner_value) in enumerate(value.items()):
			if index >= _AUDIT_MAX_COLLECTION_ITEMS:
				break
			key_text = _trim_audit_text(str(key), max_length=_AUDIT_MAX_KEY_LENGTH)
			bounded[key_text] = _bound_audit_value(inner_value, depth=depth + 1)
		return bounded

	if isinstance(value, (list, tuple)):
		return [
			_bound_audit_value(item, depth=depth + 1)
			for item in list(value)[:_AUDIT_MAX_COLLECTION_ITEMS]
		]

	return _trim_audit_text(str(value))


def _bound_audit_changes(changes: dict[str, Any] | None) -> dict[str, Any]:
	if not changes:
		return {}

	bounded_changes: dict[str, Any] = {}
	for index, (key, value) in enumerate(changes.items()):
		if index >= _AUDIT_MAX_CHANGES:
			break
		bounded_key = _trim_audit_text(str(key), max_length=_AUDIT_MAX_KEY_LENGTH)
		bounded_changes[bounded_key] = _bound_audit_value(value)
	return bounded_changes


def _is_sensitive_key(key: str) -> bool:
	normalized = key.lower()
	return any(keyword in normalized for keyword in _SENSITIVE_KEYWORDS)


def _is_sensitive_header_key(key: str) -> bool:
	normalized = key.lower()
	return any(keyword in normalized for keyword in _SENSITIVE_HEADER_KEYWORDS)


def _is_file_content_key(key: str) -> bool:
	return key.lower() in _FILE_CONTENT_FIELD_KEYS


def _should_redact_pii_for_field(field_name: str | None) -> bool:
	if field_name is None:
		return False
	normalized = field_name.lower()
	return any(keyword in normalized for keyword in _PII_REDACTION_FIELD_KEYWORDS)


def _sanitize_text(value: str, *, redact_pii: bool) -> str:
	redacted = _BEARER_TOKEN_PATTERN.sub("Bearer ***REDACTED***", value)
	redacted = _JWT_PATTERN.sub(REDACTED, redacted)
	redacted = _PROVIDER_TOKEN_PATTERN.sub(REDACTED, redacted)
	if redact_pii:
		redacted = _EMAIL_PATTERN.sub(REDACTED, redacted)
		redacted = _PHONE_PATTERN.sub(REDACTED, redacted)
		redacted = _SSN_PATTERN.sub(REDACTED, redacted)
	return redacted


def _sanitize_log_data(value: Any, *, parent_key: str | None = None) -> Any:
	if isinstance(value, dict):
		sanitized: dict[str, Any] = {}
		header_container = parent_key in _HEADER_CONTAINER_KEYS
		for key, inner_value in value.items():
			key_str = str(key)
			if header_container and _is_sensitive_header_key(key_str):
				continue
			if _is_file_content_key(key_str):
				sanitized[key_str] = "[omitted]"
				continue
			sanitized[key_str] = (
				REDACTED if _is_sensitive_key(key_str) else _sanitize_log_data(inner_value, parent_key=key_str.lower())
			)
		return sanitized
	if isinstance(value, str):
		return _sanitize_text(value, redact_pii=_should_redact_pii_for_field(parent_key))
	if isinstance(value, list):
		return [_sanitize_log_data(item, parent_key=parent_key) for item in value]
	if isinstance(value, tuple):
		return tuple(_sanitize_log_data(item, parent_key=parent_key) for item in value)
	return value


def sanitize_log_data(value: Any) -> Any:
	return _sanitize_log_data(value)


def safe_error_message(message: str) -> str:
	"""Redact credentials/tokens before exposing messages externally."""
	return _sanitize_text(message, redact_pii=False)


def _serialize_role(role: Any) -> str:
	if hasattr(role, "value"):
		return str(role.value)
	return str(role).lower()


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

	def log_admin_audit_event(
		self,
		*,
		actor_id: str,
		actor_role: Any,
		resource_type: str,
		action: str,
		resource_id: str,
		changes: dict[str, Any] | None = None,
	) -> LogEntry:
		if resource_type not in _AUDIT_RESOURCE_TYPES:
			raise ValueError(f"Unsupported audit resource_type: {resource_type}")
		if action not in _AUDIT_ACTIONS:
			raise ValueError(f"Unsupported audit action: {action}")

		bounded_changes = _bound_audit_changes(changes)

		return self.emit(
			f"audit.{resource_type}.{action}",
			actor_id=actor_id,
			actor_role=_serialize_role(actor_role),
			resource_type=resource_type,
			action=action,
			resource_id=resource_id,
			changes=bounded_changes,
			retention_days=AUDIT_LOG_RETENTION_DAYS,
		)
