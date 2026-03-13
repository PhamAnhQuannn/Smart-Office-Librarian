"""Minimal backend app facade used by the current integration suites."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rate_limit import (
	InMemoryRateLimiter,
	RateLimitError,
	RateLimitLease,
	enforce_query_rate_limit,
)
from app.api.v1.routes.feedback_routes import FeedbackSubmission, submit_feedback
from app.api.v1.routes.metrics_routes import get_metrics_response
from app.core.logging import InMemoryStructuredLogger
from app.core.metrics import (
	QUERY_REQUESTS_TOTAL,
	RETRIEVAL_FAILURES_TOTAL,
	InMemoryMetricsRegistry,
)
from app.core.security import AuthenticatedUser, AuthenticationError


def _sse_headers() -> dict[str, str]:
	return {
		"Content-Type": "text/event-stream",
		"Cache-Control": "no-cache",
		"Connection": "keep-alive",
	}


def _json_headers() -> dict[str, str]:
	return {"Content-Type": "application/json"}


def _error_response(
	*,
	status_code: int,
	error_code: str,
	message: str,
	details: dict[str, Any] | None = None,
	retry_after_seconds: int | None = None,
) -> dict[str, Any]:
	headers = _json_headers()
	if retry_after_seconds is not None:
		headers["Retry-After"] = str(retry_after_seconds)
	return {
		"status_code": status_code,
		"headers": headers,
		"body": {
			"error_code": error_code,
			"message": message,
			"request_id": str(uuid.uuid4()),
			"details": details or {},
		},
	}


def build_query_events(
	*,
	query_log_id: str,
	mode: str,
	refusal_reason: str | None,
	sources: list[dict[str, Any]],
	token_events: list[str] | None = None,
	confidence: str = "LOW",
) -> list[dict[str, Any]]:
	events: list[dict[str, Any]] = [
		{
			"type": "start",
			"mode": mode,
			"query_log_id": query_log_id,
			"model_id": "gpt-4o-mini",
			"index_version": 1,
			"namespace": "dev",
		}
	]

	if mode == "answer":
		for token in token_events or []:
			events.append({"type": "token", "text": token})

	events.append(
		{
			"type": "complete",
			"mode": mode,
			"query_log_id": query_log_id,
			"confidence": confidence,
			"refusal_reason": refusal_reason,
			"sources": sources[:3],
		}
	)
	return events


def render_sse(
	events: list[dict[str, Any]],
	*,
	split_multiline_data: bool = False,
	include_comments: bool = False,
	include_non_data_lines: bool = False,
) -> str:
	lines: list[str] = []
	if include_comments:
		lines.append(": stream warmup")
		lines.append("")

	for event in events:
		if split_multiline_data:
			for payload_line in json.dumps(event, indent=2).splitlines():
				lines.append(f"data: {payload_line}")
		else:
			lines.append(f"data: {json.dumps(event)}")

		if include_non_data_lines:
			lines.append("event: ignored")
		lines.append("")

	return "\n".join(lines)


class EmbedlyzerApp:
	def __init__(
		self,
		*,
		rate_limiter: InMemoryRateLimiter | None = None,
		logger: InMemoryStructuredLogger | None = None,
		metrics: InMemoryMetricsRegistry | None = None,
	) -> None:
		self.rate_limiter = rate_limiter or InMemoryRateLimiter()
		self.logger = logger or InMemoryStructuredLogger()
		self.metrics = metrics or InMemoryMetricsRegistry()

	def query_request(
		self,
		*,
		authorization: str | None,
		jwt_secret: str,
		now: float | None = None,
		mode: str = "answer",
		refusal_reason: str | None = None,
		sources: list[dict[str, Any]] | None = None,
		token_events: list[str] | None = None,
		confidence: str = "LOW",
		auto_release: bool = True,
		query_text: str = "",
		request_metadata: dict[str, Any] | None = None,
	) -> dict[str, Any]:
		try:
			user = get_current_user(authorization or "", jwt_secret=jwt_secret)
		except AuthenticationError as exc:
			return _error_response(
				status_code=401,
				error_code=exc.error_code,
				message=str(exc),
			)

		return self.query(
			user=user,
			now=now,
			mode=mode,
			refusal_reason=refusal_reason,
			sources=sources,
			token_events=token_events,
			confidence=confidence,
			auto_release=auto_release,
			query_text=query_text,
			request_metadata=request_metadata,
		)

	def query(
		self,
		*,
		user: AuthenticatedUser,
		now: float | None = None,
		mode: str = "answer",
		refusal_reason: str | None = None,
		sources: list[dict[str, Any]] | None = None,
		token_events: list[str] | None = None,
		confidence: str = "LOW",
		auto_release: bool = True,
		query_text: str = "",
		request_metadata: dict[str, Any] | None = None,
	) -> dict[str, Any]:
		try:
			lease = enforce_query_rate_limit(user, self.rate_limiter, now=now)
		except RateLimitError as exc:
			result = (
				"concurrency_limited"
				if exc.error_code == "RATE_LIMIT_CONCURRENCY_EXCEEDED"
				else "rate_limited"
			)
			self.metrics.increment(QUERY_REQUESTS_TOTAL, result=result)
			details = {}
			if exc.retry_after_seconds is not None:
				details["retry_after_seconds"] = exc.retry_after_seconds
			return _error_response(
				status_code=429,
				error_code=exc.error_code,
				message=exc.message,
				details=details,
				retry_after_seconds=exc.retry_after_seconds,
			)

		self.metrics.increment(QUERY_REQUESTS_TOTAL, result="accepted")
		query_log_id = str(uuid.uuid4())
		response_sources = (sources or [])[:3]

		if refusal_reason is not None:
			self.metrics.increment(RETRIEVAL_FAILURES_TOTAL, reason=refusal_reason)
			self.logger.log_retrieval_failure(
				user_id=user.user_id,
				query_log_id=query_log_id,
				query_text=query_text,
				reason=refusal_reason,
				source_count=len(response_sources),
				request_metadata=request_metadata,
			)

		response = {
			"status_code": 200,
			"headers": _sse_headers(),
			"body": render_sse(
				build_query_events(
					query_log_id=query_log_id,
					mode=mode,
					refusal_reason=refusal_reason,
					sources=response_sources,
					token_events=token_events,
					confidence=confidence,
				)
			),
		}

		if auto_release:
			lease.release()
		else:
			response["lease"] = lease
		return response

	def feedback_request(
		self,
		*,
		authorization: str | None,
		jwt_secret: str,
		query_log_id: str,
		vote: str,
		comment: str | None = None,
		metadata: dict[str, Any] | None = None,
	) -> dict[str, Any]:
		try:
			user = get_current_user(authorization or "", jwt_secret=jwt_secret)
		except AuthenticationError as exc:
			return _error_response(
				status_code=401,
				error_code=exc.error_code,
				message=str(exc),
			)

		try:
			return submit_feedback(
				FeedbackSubmission(
					query_log_id=query_log_id,
					vote=vote,
					comment=comment,
					metadata=metadata,
				),
				user=user,
				logger=self.logger,
				metrics=self.metrics,
			)
		except ValueError as exc:
			return _error_response(
				status_code=400,
				error_code="VALIDATION_ERROR",
				message=str(exc),
			)

	def metrics_endpoint(self) -> dict[str, Any]:
		return get_metrics_response(self.metrics)


def release_query_lease(response: dict[str, Any]) -> None:
	lease = response.get("lease")
	if isinstance(lease, RateLimitLease):
		lease.release()
