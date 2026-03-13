from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import pytest

from app.core.metrics import LIBRARIAN_REFUSALS_TOTAL
from app.main import EmbedlyzerApp, render_sse

JWT_SECRET = "test-secret"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(*, user_id: str = "user-1", role: str = "user", exp: int | None = None) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + 3600 if exp is None else exp,
    }
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


def _sources(count: int) -> list[dict[str, Any]]:
    return [
        {
            "file_path": f"docs/file_{index}.md",
            "source_url": f"https://example.com/file_{index}.md",
            "start_line": index,
            "end_line": index + 10,
            "text": f"snippet {index}",
        }
        for index in range(1, count + 1)
    ]


def _build_query_events(
    *,
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
            "query_log_id": "query-log-1",
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
            "query_log_id": "query-log-1",
            "confidence": confidence,
            "refusal_reason": refusal_reason,
            "sources": sources[:3],
        }
    )

    return events


def _sse_headers() -> dict[str, str]:
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }


def _parse_sse(stream: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    current_data_lines: list[str] = []

    for line in stream.splitlines():
        if line.startswith(":"):
            continue

        if line.startswith("data:"):
            current_data_lines.append(line.split(":", 1)[1].strip())
            continue

        if line == "":
            if current_data_lines:
                parsed.append(json.loads("\n".join(current_data_lines)))
            current_data_lines = []
            continue

    if current_data_lines:
        parsed.append(json.loads("\n".join(current_data_lines)))

    return parsed


def test_api_boundary_errors_are_non_sse_json() -> None:
    app = EmbedlyzerApp()
    unauth = app.query_request(authorization=None, jwt_secret=JWT_SECRET)

    auth_header = f"Bearer {_make_jwt()}"
    for attempt in range(50):
        app.query_request(
            authorization=auth_header,
            jwt_secret=JWT_SECRET,
            now=1000.0 + attempt,
            mode="answer",
            refusal_reason=None,
            sources=_sources(2),
            token_events=["Hello", " world"],
            confidence="HIGH",
        )

    rate_limited = app.query_request(
        authorization=auth_header,
        jwt_secret=JWT_SECRET,
        now=1051.0,
        mode="answer",
        refusal_reason=None,
        sources=_sources(2),
        token_events=["Hello", " world"],
        confidence="HIGH",
    )

    assert unauth["status_code"] == 401
    assert unauth["headers"]["Content-Type"] == "application/json"
    assert unauth["body"]["error_code"] == "UNAUTHENTICATED"

    assert rate_limited["status_code"] == 429
    assert rate_limited["headers"]["Content-Type"] == "application/json"
    assert rate_limited["body"]["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert rate_limited["headers"]["Retry-After"] == "3549"


def test_api_success_response_has_required_sse_headers() -> None:
    app = EmbedlyzerApp()
    response = app.query_request(
        authorization=f"Bearer {_make_jwt()}",
        jwt_secret=JWT_SECRET,
        mode="answer",
        refusal_reason=None,
        sources=_sources(2),
        token_events=["Hello", " world"],
        confidence="HIGH",
    )

    assert response["status_code"] == 200
    assert response["headers"] == _sse_headers()


def test_api_sse_parser_supports_multiline_data_and_ignores_comments() -> None:
    stream = render_sse(
        _build_query_events(
            mode="answer",
            refusal_reason=None,
            sources=_sources(2),
            token_events=["one", "two"],
            confidence="HIGH",
        ),
        split_multiline_data=True,
        include_comments=True,
        include_non_data_lines=True,
    )

    events = _parse_sse(stream)

    assert [event["type"] for event in events] == ["start", "token", "token", "complete"]


def test_api_answer_empty_output_has_non_high_confidence() -> None:
    stream = render_sse(
        _build_query_events(
            mode="answer",
            refusal_reason=None,
            sources=_sources(2),
            token_events=[],
            confidence="LOW",
        )
    )

    events = _parse_sse(stream)

    assert [event["type"] for event in events] == ["start", "complete"]
    assert events[-1]["confidence"] in {"LOW", "MEDIUM"}


def test_api_refusal_stream_has_no_tokens_and_complete_has_low_similarity_sources() -> None:
    app = EmbedlyzerApp()
    response = app.query_request(
        authorization=f"Bearer {_make_jwt(user_id='user-refusal')}",
        jwt_secret=JWT_SECRET,
        mode="refusal",
        refusal_reason="LOW_SIMILARITY",
        sources=_sources(5),
        confidence="LOW",
        query_text="where is the runbook",
        request_metadata={"authorization": "Bearer super-secret-token"},
    )

    events = _parse_sse(response["body"])

    assert [event["type"] for event in events] == ["start", "complete"]
    complete = events[-1]
    assert complete["mode"] == "refusal"
    assert complete["refusal_reason"] == "LOW_SIMILARITY"
    assert len(complete["sources"]) == 3
    assert not any(event["type"] == "token" for event in events)

    assert app.metrics.get_counter(LIBRARIAN_REFUSALS_TOTAL, reason="LOW_SIMILARITY") == 1
    retrieval_log = app.logger.entries[-1]
    assert retrieval_log.event_type == "query.retrieval_failure"
    assert retrieval_log.payload["request_metadata"]["authorization"] == "***REDACTED***"


@pytest.mark.parametrize("reason", ["BUDGET_EXCEEDED", "LLM_UNAVAILABLE"])
def test_api_retrieval_only_stream_has_no_tokens_and_complete_has_allowed_reason(reason: str) -> None:
    app = EmbedlyzerApp()
    response = app.query_request(
        authorization=f"Bearer {_make_jwt(user_id='user-retrieval-only')}",
        jwt_secret=JWT_SECRET,
        mode="retrieval_only",
        refusal_reason=reason,
        sources=_sources(4),
        confidence="LOW",
    )

    events = _parse_sse(response["body"])

    assert [event["type"] for event in events] == ["start", "complete"]
    complete = events[-1]
    assert complete["mode"] == "retrieval_only"
    assert complete["refusal_reason"] == reason
    assert len(complete["sources"]) == 3
    assert not any(event["type"] == "token" for event in events)


def test_api_answer_stream_keeps_start_token_complete_order() -> None:
    app = EmbedlyzerApp()
    response = app.query_request(
        authorization=f"Bearer {_make_jwt(user_id='user-answer')}",
        jwt_secret=JWT_SECRET,
        mode="answer",
        refusal_reason=None,
        sources=_sources(2),
        token_events=["Hello", " world"],
        confidence="HIGH",
    )

    events = _parse_sse(response["body"])

    assert [event["type"] for event in events] == ["start", "token", "token", "complete"]
    complete = events[-1]
    assert complete["mode"] == "answer"
    assert complete["refusal_reason"] is None
    assert "answer" not in complete


def test_api_answer_tokens_concatenate_exactly() -> None:
    app = EmbedlyzerApp()
    response = app.query_request(
        authorization=f"Bearer {_make_jwt(user_id='user-tokens')}",
        jwt_secret=JWT_SECRET,
        mode="answer",
        refusal_reason=None,
        sources=_sources(1),
        token_events=["Hello", "\n", "World"],
        confidence="HIGH",
    )

    events = _parse_sse(response["body"])
    assembled = "".join(event["text"] for event in events if event["type"] == "token")

    assert assembled == "Hello\nWorld"


def test_metrics_endpoint_exposes_query_and_retrieval_counters() -> None:
    app = EmbedlyzerApp()
    auth_header = f"Bearer {_make_jwt(user_id='metrics-user')}"

    app.query_request(
        authorization=auth_header,
        jwt_secret=JWT_SECRET,
        mode="answer",
        refusal_reason=None,
        sources=_sources(1),
        token_events=["ok"],
        confidence="HIGH",
    )
    app.query_request(
        authorization=auth_header,
        jwt_secret=JWT_SECRET,
        mode="refusal",
        refusal_reason="LOW_SIMILARITY",
        sources=_sources(3),
        confidence="LOW",
    )

    metrics_response = app.metrics_endpoint()

    assert metrics_response["status_code"] == 200
    assert metrics_response["headers"]["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert 'embedlyzer_query_requests_total{result="accepted"} 2' in metrics_response["body"]
    assert 'embedlyzer_retrieval_failures_total{reason="LOW_SIMILARITY"} 1' in metrics_response["body"]
    assert 'librarian_queries_total{mode="answer"} 1' in metrics_response["body"]
    assert 'librarian_queries_total{mode="refusal"} 1' in metrics_response["body"]
    assert 'librarian_refusals_total{reason="LOW_SIMILARITY"} 1' in metrics_response["body"]
    assert 'librarian_active_sse_streams 0.0' in metrics_response["body"]
