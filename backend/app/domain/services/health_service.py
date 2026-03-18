"""Health service: composite readiness + liveness checks.

Each probe is a callable that returns (ok: bool, latency_ms: float).
All probes are checked on ``check_readiness()``; only a fast in-process
check is done on ``check_liveness()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

Probe = Callable[[int], tuple[bool, float]]


@dataclass(frozen=True)
class ComponentStatus:
    name: str
    ok: bool
    latency_ms: float


@dataclass
class HealthReport:
    overall_ok: bool
    components: list[ComponentStatus]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.overall_ok else "degraded",
            "components": [
                {"name": c.name, "ok": c.ok, "latency_ms": round(c.latency_ms, 1)}
                for c in self.components
            ],
        }


class HealthService:
    """Aggregates liveness and readiness probes."""

    def __init__(
        self,
        *,
        postgres_probe: Probe | None = None,
        redis_probe: Probe | None = None,
        pinecone_probe: Probe | None = None,
        timeout_ms: int = 2000,
    ) -> None:
        self._probes: list[tuple[str, Probe]] = []
        if postgres_probe:
            self._probes.append(("postgres", postgres_probe))
        if redis_probe:
            self._probes.append(("redis", redis_probe))
        if pinecone_probe:
            self._probes.append(("pinecone", pinecone_probe))
        self._timeout_ms = timeout_ms

    def check_liveness(self) -> HealthReport:
        """Fast in-process liveness check (always returns ok)."""
        return HealthReport(overall_ok=True, components=[])

    def check_readiness(self) -> HealthReport:
        """Run all dependency probes and return aggregated status."""
        components: list[ComponentStatus] = []
        all_ok = True
        for name, probe in self._probes:
            try:
                ok, latency_ms = probe(self._timeout_ms)
            except Exception:  # noqa: BLE001
                ok, latency_ms = False, float(self._timeout_ms)
            if not ok:
                all_ok = False
            components.append(ComponentStatus(name=name, ok=ok, latency_ms=latency_ms))
        return HealthReport(overall_ok=all_ok, components=components)

    # ── convenience aliases used by health_routes ──────────────────────────────

    def check_health(self) -> dict[str, Any]:
        """Return liveness status as a plain dict (used by GET /health)."""
        report = self.check_liveness()
        return report.as_dict()

    def check_ready(self) -> dict[str, Any]:
        """Return readiness status as a plain dict (used by GET /ready)."""
        report = self.check_readiness()
        return {"ready": report.overall_ok, **report.as_dict()}
