"""Minimal in-memory metrics registry for FR-5 observability slices."""

from __future__ import annotations

from collections import defaultdict

QUERY_REQUESTS_TOTAL = "embedlyzer_query_requests_total"
RETRIEVAL_FAILURES_TOTAL = "embedlyzer_retrieval_failures_total"
FEEDBACK_TOTAL = "embedlyzer_feedback_total"


class InMemoryMetricsRegistry:
	def __init__(self) -> None:
		self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = defaultdict(int)

	def increment(self, name: str, amount: int = 1, **labels: str) -> int:
		key = (name, tuple(sorted((label, str(value)) for label, value in labels.items())))
		self._counters[key] += amount
		return self._counters[key]

	def get_counter(self, name: str, **labels: str) -> int:
		key = (name, tuple(sorted((label, str(value)) for label, value in labels.items())))
		return self._counters.get(key, 0)

	def render_prometheus(self) -> str:
		lines: list[str] = []
		seen_names: set[str] = set()

		for name, _labels in sorted(self._counters):
			if name not in seen_names:
				lines.append(f"# TYPE {name} counter")
				seen_names.add(name)

		for (name, labels), value in sorted(self._counters.items()):
			rendered_labels = ""
			if labels:
				label_text = ",".join(f'{label}="{label_value}"' for label, label_value in labels)
				rendered_labels = f"{{{label_text}}}"
			lines.append(f"{name}{rendered_labels} {value}")

		return "\n".join(lines) + ("\n" if lines else "")
