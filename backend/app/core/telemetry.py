"""Lightweight telemetry helpers for stage and TTFT latency tracking.

Includes optional OpenTelemetry bootstrap (NFR-6.2). When the opentelemetry-sdk
package is installed, ``setup_telemetry()`` initialises the SDK with an OTLP
exporter and returns a live tracer.  When the package is absent the function
returns a no-op tracer so that all call-sites remain identical.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Protocol, runtime_checkable

from app.core.metrics import (
	LIBRARIAN_STAGE_LATENCY_MS,
	LIBRARIAN_TTFT_MS,
	InMemoryMetricsRegistry,
)


# ---------------------------------------------------------------------------
# OpenTelemetry bootstrap (NFR-6.2)
# ---------------------------------------------------------------------------

@runtime_checkable
class _Span(Protocol):
	"""Minimal span interface satisfied by both real OTEL spans and the no-op."""

	def set_attribute(self, key: str, value: Any) -> None: ...
	def end(self) -> None: ...


@runtime_checkable
class _Tracer(Protocol):
	"""Minimal tracer interface satisfied by both real OTEL tracers and the no-op."""

	def start_span(self, name: str, **kwargs: Any) -> _Span: ...


class _NoOpSpan:
	"""No-op span used when the OpenTelemetry SDK is absent."""

	def set_attribute(self, key: str, value: Any) -> None:  # noqa: ARG002
		pass

	def end(self) -> None:
		pass


class _NoOpTracer:
	"""No-op tracer returned when the OpenTelemetry SDK is absent."""

	def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:  # noqa: ARG002
		return _NoOpSpan()


def setup_telemetry(
	*,
	service_name: str = "embedlyzer-api",
	otlp_endpoint: str | None = None,
	enabled: bool = True,
) -> Any:
	"""Bootstrap OpenTelemetry tracing (NFR-6.2).

	Returns a real tracer if the ``opentelemetry-sdk`` package is installed and
	``enabled=True``; otherwise returns a ``_NoOpTracer`` so call-sites never need
	to guard against ``None``.

	Args:
		service_name: Logical service name emitted in trace metadata.
		otlp_endpoint: OTLP/gRPC collector endpoint, e.g.
			``"http://localhost:4317"``.  Defaults to the OTEL SDK default
			(``http://localhost:4317``) when ``None``.
		enabled: Set ``False`` (or leave the SDK uninstalled) to return a no-op
			tracer.  Useful for disabling tracing in test environments.
	"""
	if not enabled:
		return _NoOpTracer()

	try:
		from opentelemetry import trace  # type: ignore[import-not-found]
		from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
		from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
		from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-not-found]
		from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
			OTLPSpanExporter,
		)
	except ModuleNotFoundError:
		# OpenTelemetry SDK is not installed — return a no-op tracer so the
		# application boots normally regardless of deployment environment.
		return _NoOpTracer()

	resource = Resource.create({"service.name": service_name})
	provider = TracerProvider(resource=resource)

	exporter_kwargs: dict[str, Any] = {}
	if otlp_endpoint is not None:
		exporter_kwargs["endpoint"] = otlp_endpoint

	exporter = OTLPSpanExporter(**exporter_kwargs)
	provider.add_span_processor(BatchSpanProcessor(exporter))
	trace.set_tracer_provider(provider)
	return trace.get_tracer(service_name)


# ---------------------------------------------------------------------------
# In-memory telemetry (stage span recording + histogram emission)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TelemetrySpanRecord:
	stage: str
	duration_ms: float


class InMemoryTelemetry:
	def __init__(self, metrics: InMemoryMetricsRegistry) -> None:
		self._metrics = metrics
		self._records: list[TelemetrySpanRecord] = []

	@property
	def records(self) -> list[TelemetrySpanRecord]:
		return list(self._records)

	@contextmanager
	def stage_span(self, stage: str) -> Iterator[None]:
		start = time.perf_counter()
		try:
			yield
		finally:
			duration_ms = (time.perf_counter() - start) * 1000.0
			self._records.append(TelemetrySpanRecord(stage=stage, duration_ms=duration_ms))
			self._metrics.observe_histogram(
				LIBRARIAN_STAGE_LATENCY_MS,
				duration_ms,
				stage=stage,
			)

	def record_ttft_ms(self, value_ms: float) -> None:
		self._metrics.observe_histogram(LIBRARIAN_TTFT_MS, value_ms)
