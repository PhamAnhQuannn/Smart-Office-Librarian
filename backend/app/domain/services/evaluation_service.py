"""Evaluation service: compute pass-rates and aggregate golden-question metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationSummary:
    total: int
    passed: int
    failed: int
    pass_rate: float
    namespace: str
    index_version: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "namespace": self.namespace,
            "index_version": self.index_version,
        }


class EvaluationService:
    """Queries the DB evaluation results table and returns aggregated metrics."""

    def __init__(self, evaluation_repo: Any | None = None) -> None:
        self._repo = evaluation_repo

    def get_summary(self, *, namespace: str, index_version: int) -> EvaluationSummary:
        """Return pass/fail counts and pass-rate for a namespace+index_version."""
        if self._repo is not None and hasattr(self._repo, "pass_rate"):
            rate = self._repo.pass_rate(namespace=namespace, index_version=index_version)
            total = getattr(self._repo, "count", lambda **_: 0)(namespace=namespace, index_version=index_version)
            passed = round(rate * total)
            failed = total - passed
        else:
            total = passed = failed = 0
            rate = 0.0

        return EvaluationSummary(
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=rate,
            namespace=namespace,
            index_version=index_version,
        )

    def record_result(
        self,
        *,
        namespace: str,
        index_version: int,
        question_id: str,
        passed: bool,
        score: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Persist a single evaluation result.  No-ops when repo is absent."""
        if self._repo is None or not hasattr(self._repo, "add"):
            return
        from app.db.models import EvaluationResultModel  # type: ignore[import]
        record = EvaluationResultModel(
            namespace=namespace,
            index_version=index_version,
            question_id=question_id,
            passed=passed,
            score=score,
            details=details or {},
        )
        self._repo.add(record)
