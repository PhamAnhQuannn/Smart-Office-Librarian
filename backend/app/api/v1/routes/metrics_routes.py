"""Canonical metrics endpoint helpers."""

from __future__ import annotations

from typing import Any

from app.core.metrics import InMemoryMetricsRegistry


def get_metrics_response(metrics: InMemoryMetricsRegistry) -> dict[str, Any]:
	return {
		"status_code": 200,
		"headers": {"Content-Type": "text/plain; version=0.0.4; charset=utf-8"},
		"body": metrics.render_prometheus(),
	}
