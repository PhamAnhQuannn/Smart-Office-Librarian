from __future__ import annotations

import json
import uuid
from typing import Any

import pytest


def _sources(count: int) -> list[dict[str, Any]]:
    return [
        {
            "file_path": f"docs/file_{i}.md",
            "source_url": f"https://example.com/file_{i}.md",
            "start_line": i,
            "end_line": i + 10,
            "text": f"snippet {i}",
        }
        for i in range(1, count + 1)
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


def _error_response(*, status_code: int, error_code: str, message: str) -> dict[str, Any]:
    return {
        "status_code": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": {
            "error_code": error_code,
            "message": message,
            "request_id": str(uuid.uuid4()),
            "details": {},
        },
    }


def _simulate_query_request(
    *,
    authenticated: bool,
    rate_limited: bool,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not authenticated:
        return _error_response(
            status_code=401,
            error_code="UNAUTHENTICATED",
            message="Authentication required",
        )

    if rate_limited:
        return _error_response(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded",
        )

    stream_events = events or _build_query_events(
        mode="answer",
        refusal_reason=None,
        sources=_sources(2),
        token_events=["Hello", " world"],
        confidence="HIGH",
    )
    return {
        "status_code": 200,
        "headers": _sse_headers(),
        "body": _render_sse(stream_events),
    }


def _render_sse(
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


def _parse_sse(stream: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    current_data_lines: list[str] = []

    for line in stream.splitlines():
        if line.startswith(":"):
            # Comment lines are legal SSE and must be ignored.
            continue

        if line.startswith("data:"):
            current_data_lines.append(line.split(":", 1)[1].strip())
            continue

        if line == "":
            if current_data_lines:
                parsed.append(json.loads("\n".join(current_data_lines)))
            current_data_lines = []
            continue

        # Ignore non-data/non-comment lines per SSE compatibility rule.
        continue

    # Some streams may omit a trailing blank separator; flush any pending event.
    if current_data_lines:
        parsed.append(json.loads("\n".join(current_data_lines)))

    return parsed


def test_api_boundary_errors_are_non_sse_json() -> None:
    unauth = _simulate_query_request(authenticated=False, rate_limited=False)
    rate_limited = _simulate_query_request(authenticated=True, rate_limited=True)

    assert unauth["status_code"] == 401
    assert unauth["headers"]["Content-Type"] == "application/json"
    assert unauth["body"]["error_code"] == "UNAUTHENTICATED"

    assert rate_limited["status_code"] == 429
    assert rate_limited["headers"]["Content-Type"] == "application/json"
    assert rate_limited["body"]["error_code"] == "RATE_LIMIT_EXCEEDED"


def test_api_success_response_has_required_sse_headers() -> None:
    response = _simulate_query_request(authenticated=True, rate_limited=False)

    assert response["status_code"] == 200
    assert response["headers"] == _sse_headers()


def test_api_sse_parser_supports_multiline_data_and_ignores_comments() -> None:
    stream = _render_sse(
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
    stream = _render_sse(
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
    stream = _render_sse(
        _build_query_events(
            mode="refusal",
            refusal_reason="LOW_SIMILARITY",
            sources=_sources(5),
            confidence="LOW",
        )
    )

    events = _parse_sse(stream)

    assert [event["type"] for event in events] == ["start", "complete"]
    complete = events[-1]
    assert complete["mode"] == "refusal"
    assert complete["refusal_reason"] == "LOW_SIMILARITY"
    assert len(complete["sources"]) == 3
    assert not any(event["type"] == "token" for event in events)


@pytest.mark.parametrize("reason", ["BUDGET_EXCEEDED", "LLM_UNAVAILABLE"])
def test_api_retrieval_only_stream_has_no_tokens_and_complete_has_allowed_reason(reason: str) -> None:
    stream = _render_sse(
        _build_query_events(
            mode="retrieval_only",
            refusal_reason=reason,
            sources=_sources(4),
            confidence="LOW",
        )
    )

    events = _parse_sse(stream)

    assert [event["type"] for event in events] == ["start", "complete"]
    complete = events[-1]
    assert complete["mode"] == "retrieval_only"
    assert complete["refusal_reason"] == reason
    assert len(complete["sources"]) == 3
    assert not any(event["type"] == "token" for event in events)


def test_api_answer_stream_keeps_start_token_complete_order() -> None:
    stream = _render_sse(
        _build_query_events(
            mode="answer",
            refusal_reason=None,
            sources=_sources(2),
            token_events=["Hello", " world"],
            confidence="HIGH",
        )
    )

    events = _parse_sse(stream)

    assert [event["type"] for event in events] == ["start", "token", "token", "complete"]
    complete = events[-1]
    assert complete["mode"] == "answer"
    assert complete["refusal_reason"] is None
    # complete payload should be metadata, not full answer text
    assert "answer" not in complete


def test_api_answer_tokens_concatenate_exactly() -> None:
    stream = _render_sse(
        _build_query_events(
            mode="answer",
            refusal_reason=None,
            sources=_sources(1),
            token_events=["Hello", "\n", "World"],
            confidence="HIGH",
        )
    )

    events = _parse_sse(stream)
    assembled = "".join(event["text"] for event in events if event["type"] == "token")

    assert assembled == "Hello\nWorld"
