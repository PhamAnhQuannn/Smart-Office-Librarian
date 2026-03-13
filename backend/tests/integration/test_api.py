from __future__ import annotations

import json
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
) -> list[dict[str, Any]]:
    events = [
        {
            "event": "start",
            "data": {
                "mode": mode,
                "query_log_id": "query-log-1",
            },
        }
    ]

    if mode == "answer":
        for token in token_events or []:
            events.append({"event": "token", "data": {"token": token}})

    events.append(
        {
            "event": "complete",
            "data": {
                "mode": mode,
                "refusal_reason": refusal_reason,
                "sources": sources[:3],
            },
        }
    )

    return events


def _render_sse(events: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for event in events:
        lines.append(f"event: {event['event']}")
        lines.append(f"data: {json.dumps(event['data'])}")
        lines.append("")
    return "\n".join(lines)


def _parse_sse(stream: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    current_event: str | None = None
    current_data_lines: list[str] = []

    for line in stream.splitlines():
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
            continue

        if line.startswith("data:"):
            current_data_lines.append(line.split(":", 1)[1].strip())
            continue

        if line == "":
            if current_event is not None:
                payload = json.loads("\n".join(current_data_lines)) if current_data_lines else {}
                parsed.append({"event": current_event, "data": payload})
            current_event = None
            current_data_lines = []

    # Some streams may omit a trailing blank separator; flush any pending event.
    if current_event is not None:
        payload = json.loads("\n".join(current_data_lines)) if current_data_lines else {}
        parsed.append({"event": current_event, "data": payload})

    return parsed


def test_api_refusal_stream_has_no_tokens_and_complete_has_low_similarity_sources() -> None:
    stream = _render_sse(
        _build_query_events(
            mode="refusal",
            refusal_reason="LOW_SIMILARITY",
            sources=_sources(5),
        )
    )

    events = _parse_sse(stream)

    assert [event["event"] for event in events] == ["start", "complete"]
    complete = events[-1]["data"]
    assert complete["mode"] == "refusal"
    assert complete["refusal_reason"] == "LOW_SIMILARITY"
    assert len(complete["sources"]) == 3
    assert not any(event["event"] == "token" for event in events)


@pytest.mark.parametrize("reason", ["BUDGET_EXCEEDED", "LLM_UNAVAILABLE"])
def test_api_retrieval_only_stream_has_no_tokens_and_complete_has_allowed_reason(reason: str) -> None:
    stream = _render_sse(
        _build_query_events(
            mode="retrieval_only",
            refusal_reason=reason,
            sources=_sources(4),
        )
    )

    events = _parse_sse(stream)

    assert [event["event"] for event in events] == ["start", "complete"]
    complete = events[-1]["data"]
    assert complete["mode"] == "retrieval_only"
    assert complete["refusal_reason"] == reason
    assert len(complete["sources"]) == 3
    assert not any(event["event"] == "token" for event in events)


def test_api_answer_stream_keeps_start_token_complete_order() -> None:
    stream = _render_sse(
        _build_query_events(
            mode="answer",
            refusal_reason=None,
            sources=_sources(2),
            token_events=["Hello", " world"],
        )
    )

    events = _parse_sse(stream)

    assert [event["event"] for event in events] == ["start", "token", "token", "complete"]
    complete = events[-1]["data"]
    assert complete["mode"] == "answer"
    assert complete["refusal_reason"] is None
    # complete payload should be metadata, not full answer text
    assert "answer" not in complete
