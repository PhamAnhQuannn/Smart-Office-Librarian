"""Evaluation result persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EvaluationResultModel
from app.db.repositories.base_repo import BaseRepository


class EvaluationRepository(BaseRepository[EvaluationResultModel]):
    model_class = EvaluationResultModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def create(self, *, dataset_name: str, question: str, passed: bool,
               expected_answer: str | None = None, actual_answer: str | None = None,
               cosine_score: float | None = None,
               latency_ms: float | None = None) -> EvaluationResultModel:
        result = EvaluationResultModel(
            dataset_name=dataset_name,
            question=question,
            passed=passed,
            expected_answer=expected_answer,
            actual_answer=actual_answer,
            cosine_score=cosine_score,
            latency_ms=latency_ms,
        )
        return self.add(result)

    def list_by_dataset(self, dataset_name: str) -> list[EvaluationResultModel]:
        stmt = select(EvaluationResultModel).where(
            EvaluationResultModel.dataset_name == dataset_name
        )
        return list(self._session.scalars(stmt))

    def pass_rate(self, dataset_name: str) -> float:
        results = self.list_by_dataset(dataset_name)
        if not results:
            return 0.0
        return sum(1 for r in results if r.passed) / len(results)
