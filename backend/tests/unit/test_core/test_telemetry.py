from __future__ import annotations

from app.core.metrics import InMemoryMetricsRegistry
from app.core.telemetry import (
    InMemoryTelemetry,
    _NoOpSpan,
    _NoOpTracer,
    setup_telemetry,
)


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


# ---------------------------------------------------------------------------
# setup_telemetry (NFR-6.2) — OTEL bootstrap tests
# ---------------------------------------------------------------------------


def test_setup_telemetry_returns_noop_tracer_when_disabled() -> None:
    """enabled=False must always yield a no-op tracer, SDK presence notwithstanding."""
    tracer = setup_telemetry(enabled=False)
    assert isinstance(tracer, _NoOpTracer)


def test_setup_telemetry_returns_tracer_type_regardless_of_sdk() -> None:
    """setup_telemetry must return a tracer-like object with start_span callable
    whether the opentelemetry SDK is installed or not."""
    tracer = setup_telemetry(service_name="test-svc", enabled=True)
    # Either a real tracer (SDK installed) or the _NoOpTracer fallback.
    assert hasattr(tracer, "start_span"), "tracer must expose start_span"


def test_noop_span_is_safe_to_call() -> None:
    """_NoOpSpan.set_attribute and .end must not raise."""
    span = _NoOpSpan()
    span.set_attribute("key", "value")
    span.set_attribute("num", 42)
    span.end()  # must not raise


def test_noop_tracer_start_span_returns_noop_span() -> None:
    tracer = _NoOpTracer()
    span = tracer.start_span("operation", attributes={"foo": "bar"})
    assert isinstance(span, _NoOpSpan)


def test_setup_telemetry_noop_tracer_start_span_is_safe() -> None:
    """Full exercise: disabled tracer -> start_span -> set_attribute -> end."""
    tracer = setup_telemetry(enabled=False)
    span = tracer.start_span("embed")
    span.set_attribute("stage", "embed")
    span.set_attribute("duration_ms", 123.4)
    span.end()  # must not raise


def test_setup_telemetry_with_custom_service_name_and_endpoint_does_not_raise() -> None:
    """Passing a custom otlp_endpoint must not raise even when the SDK is absent
    (graceful fallback to no-op tracer)."""
    tracer = setup_telemetry(
        service_name="embedlyzer-worker",
        otlp_endpoint="http://otel-collector:4317",
        enabled=True,
    )
    # Must have start_span; content depends on whether SDK is installed.
    assert hasattr(tracer, "start_span")
