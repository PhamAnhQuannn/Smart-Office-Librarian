"""Lightweight telemetry helpers for stage and TTFT latency tracking."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from app.core.metrics import (
	LIBRARIAN_STAGE_LATENCY_MS,
	LIBRARIAN_TTFT_MS,
	InMemoryMetricsRegistry,
)


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
