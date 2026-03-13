"""In-memory observability registry with Prometheus-compatible rendering."""

from __future__ import annotations

from dataclasses import dataclass

QUERY_REQUESTS_TOTAL = "embedlyzer_query_requests_total"
RETRIEVAL_FAILURES_TOTAL = "embedlyzer_retrieval_failures_total"
FEEDBACK_TOTAL = "embedlyzer_feedback_total"

# Canonical names from TESTING.md/DECISIONS.md.
LIBRARIAN_QUERIES_TOTAL = "librarian_queries_total"
LIBRARIAN_REFUSALS_TOTAL = "librarian_refusals_total"
LIBRARIAN_ERRORS_TOTAL = "librarian_errors_total"
LIBRARIAN_STAGE_LATENCY_MS = "librarian_stage_latency_ms"
LIBRARIAN_TTFT_MS = "librarian_ttft_ms"
LIBRARIAN_ACTIVE_SSE_STREAMS = "librarian_active_sse_streams"
LIBRARIAN_FEEDBACK_TOTAL = "librarian_feedback_total"

DEFAULT_HISTOGRAM_BUCKETS_MS = (50.0, 100.0, 250.0, 500.0, 1000.0, 2000.0, 3000.0)

_CANONICAL_LABELS: dict[str, set[str]] = {
	LIBRARIAN_QUERIES_TOTAL: {"mode"},
	LIBRARIAN_REFUSALS_TOTAL: {"reason"},
	LIBRARIAN_ERRORS_TOTAL: {"code"},
	LIBRARIAN_STAGE_LATENCY_MS: {"stage"},
	LIBRARIAN_TTFT_MS: set(),
	LIBRARIAN_ACTIVE_SSE_STREAMS: set(),
	LIBRARIAN_FEEDBACK_TOTAL: {"vote"},
}


@dataclass
class _HistogramSeries:
	buckets: tuple[float, ...]
	cumulative_counts: list[int]
	sum: float
	count: int


class InMemoryMetricsRegistry:
	def __init__(self) -> None:
		self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
		self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
		self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], _HistogramSeries] = {}

	def _normalize_labels(self, name: str, labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
		allowed = _CANONICAL_LABELS.get(name)
		if allowed is not None:
			unexpected = sorted(label for label in labels if label not in allowed)
			if unexpected:
				raise ValueError(
					f"Unexpected labels for metric '{name}': {', '.join(unexpected)}"
				)
		return tuple(sorted((label, str(value)) for label, value in labels.items()))

	def increment(self, name: str, amount: int = 1, **labels: str) -> int:
		normalized_labels = self._normalize_labels(name, labels)
		key = (name, normalized_labels)
		self._counters[key] = self._counters.get(key, 0) + amount
		return self._counters[key]

	def set_gauge(self, name: str, value: float, **labels: str) -> float:
		normalized_labels = self._normalize_labels(name, labels)
		key = (name, normalized_labels)
		self._gauges[key] = float(value)
		return self._gauges[key]

	def observe_histogram(
		self,
		name: str,
		value: float,
		*,
		buckets: tuple[float, ...] = DEFAULT_HISTOGRAM_BUCKETS_MS,
		**labels: str,
	) -> None:
		normalized_labels = self._normalize_labels(name, labels)
		key = (name, normalized_labels)
		series = self._histograms.get(key)
		if series is None:
			series = _HistogramSeries(
				buckets=buckets,
				cumulative_counts=[0 for _ in range(len(buckets) + 1)],
				sum=0.0,
				count=0,
			)
			self._histograms[key] = series
		elif series.buckets != buckets:
			raise ValueError(f"Histogram buckets mismatch for metric '{name}'")

		index = len(series.buckets)
		for bucket_index, boundary in enumerate(series.buckets):
			if value <= boundary:
				index = bucket_index
				break

		for cumulative_index in range(index, len(series.cumulative_counts)):
			series.cumulative_counts[cumulative_index] += 1

		series.sum += float(value)
		series.count += 1

	def get_counter(self, name: str, **labels: str) -> int:
		normalized_labels = self._normalize_labels(name, labels)
		key = (name, normalized_labels)
		return self._counters.get(key, 0)

	def render_prometheus(self) -> str:
		lines: list[str] = []

		for name in sorted({metric_name for metric_name, _ in self._counters}):
			lines.append(f"# TYPE {name} counter")
		for (name, labels), value in sorted(self._counters.items()):
			lines.append(f"{name}{self._render_labels(labels)} {value}")

		for name in sorted({metric_name for metric_name, _ in self._gauges}):
			lines.append(f"# TYPE {name} gauge")
		for (name, labels), value in sorted(self._gauges.items()):
			lines.append(f"{name}{self._render_labels(labels)} {value}")

		for name in sorted({metric_name for metric_name, _ in self._histograms}):
			lines.append(f"# TYPE {name} histogram")
		for (name, labels), series in sorted(self._histograms.items()):
			for index, boundary in enumerate(series.buckets):
				bucket_labels = list(labels) + [("le", self._format_bucket(boundary))]
				lines.append(
					f"{name}_bucket{self._render_labels(tuple(bucket_labels))} {series.cumulative_counts[index]}"
				)
			infinity_labels = list(labels) + [("le", "+Inf")]
			lines.append(
				f"{name}_bucket{self._render_labels(tuple(infinity_labels))} {series.cumulative_counts[-1]}"
			)
			lines.append(f"{name}_sum{self._render_labels(labels)} {series.sum}")
			lines.append(f"{name}_count{self._render_labels(labels)} {series.count}")

		return "\n".join(lines) + ("\n" if lines else "")

	@staticmethod
	def _render_labels(labels: tuple[tuple[str, str], ...]) -> str:
		if not labels:
			return ""
		label_text = ",".join(f'{label}="{label_value}"' for label, label_value in labels)
		return f"{{{label_text}}}"

	@staticmethod
	def _format_bucket(value: float) -> str:
		if value.is_integer():
			return str(int(value))
		return str(value)
