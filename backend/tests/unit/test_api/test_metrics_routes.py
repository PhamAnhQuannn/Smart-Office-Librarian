from __future__ import annotations

import pytest

from app.api.v1.routes.metrics_routes import get_metrics_response
from app.core.metrics import (
    LIBRARIAN_ACTIVE_SSE_STREAMS,
    LIBRARIAN_ERRORS_TOTAL,
    LIBRARIAN_QUERIES_TOTAL,
    LIBRARIAN_STAGE_LATENCY_MS,
    LIBRARIAN_TTFT_MS,
    InMemoryMetricsRegistry,
)


def test_metrics_route_returns_prometheus_text_response() -> None:
    metrics = InMemoryMetricsRegistry()
    metrics.increment(LIBRARIAN_QUERIES_TOTAL, mode="answer")

    response = get_metrics_response(metrics)

    assert response["status_code"] == 200
    assert response["headers"]["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"
    assert "# TYPE librarian_queries_total counter" in response["body"]


def test_metrics_route_renders_histograms_and_gauges_with_expected_families() -> None:
    metrics = InMemoryMetricsRegistry()
    metrics.increment(LIBRARIAN_ERRORS_TOTAL, code="HTTP_4XX")
    metrics.set_gauge(LIBRARIAN_ACTIVE_SSE_STREAMS, 2)
    metrics.observe_histogram(LIBRARIAN_STAGE_LATENCY_MS, 187.2, stage="vector")
    metrics.observe_histogram(LIBRARIAN_TTFT_MS, 321.0)

    body = get_metrics_response(metrics)["body"]

    assert "# TYPE librarian_active_sse_streams gauge" in body
    assert "librarian_active_sse_streams 2.0" in body

    assert "# TYPE librarian_stage_latency_ms histogram" in body
    assert "librarian_stage_latency_ms_bucket" in body
    assert "stage=\"vector\"" in body
    assert "le=\"" in body
    assert "librarian_stage_latency_ms_sum{stage=\"vector\"}" in body
    assert "librarian_stage_latency_ms_count{stage=\"vector\"}" in body

    assert "# TYPE librarian_ttft_ms histogram" in body
    assert "librarian_ttft_ms_bucket{le=\"" in body
    assert "librarian_ttft_ms_sum" in body
    assert "librarian_ttft_ms_count" in body


def test_metrics_route_rejects_unbounded_labels_for_canonical_metrics() -> None:
    metrics = InMemoryMetricsRegistry()

    with pytest.raises(ValueError):
        metrics.increment(LIBRARIAN_QUERIES_TOTAL, mode="answer", user_id="u-1")
