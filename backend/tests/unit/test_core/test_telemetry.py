from __future__ import annotations

from app.core.metrics import InMemoryMetricsRegistry
from app.core.telemetry import InMemoryTelemetry


def test_stage_span_records_duration_and_updates_stage_histogram() -> None:
    metrics = InMemoryMetricsRegistry()
    telemetry = InMemoryTelemetry(metrics)

    with telemetry.stage_span("vector"):
        _ = sum(range(250))

    assert len(telemetry.records) == 1
    assert telemetry.records[0].stage == "vector"
    assert telemetry.records[0].duration_ms >= 0.0

    body = metrics.render_prometheus()
    assert "# TYPE librarian_stage_latency_ms histogram" in body
    assert "librarian_stage_latency_ms_bucket{stage=\"vector\",le=\"" in body
    assert "librarian_stage_latency_ms_sum{stage=\"vector\"}" in body
    assert "librarian_stage_latency_ms_count{stage=\"vector\"}" in body


def test_record_ttft_writes_ttft_histogram_family() -> None:
    metrics = InMemoryMetricsRegistry()
    telemetry = InMemoryTelemetry(metrics)

    telemetry.record_ttft_ms(420.5)

    body = metrics.render_prometheus()
    assert "# TYPE librarian_ttft_ms histogram" in body
    assert "librarian_ttft_ms_bucket{le=\"" in body
    assert "librarian_ttft_ms_sum" in body
    assert "librarian_ttft_ms_count" in body
