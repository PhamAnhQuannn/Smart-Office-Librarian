"""Threshold configuration persistence repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ThresholdConfigModel
from app.db.repositories.base_repo import BaseRepository


class ThresholdsRepository(BaseRepository[ThresholdConfigModel]):
    model_class = ThresholdConfigModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_for_namespace(self, namespace: str, index_version: int) -> ThresholdConfigModel | None:
        stmt = select(ThresholdConfigModel).where(
            ThresholdConfigModel.namespace == namespace,
            ThresholdConfigModel.index_version == index_version,
        )
        return self._session.scalars(stmt).first()

    def upsert(self, *, namespace: str, index_version: int, threshold: float,
               updated_by: str | None = None) -> ThresholdConfigModel:
        existing = self.get_for_namespace(namespace, index_version)
        if existing:
            existing.threshold = threshold
            existing.updated_by = updated_by
            self._session.flush()
            return existing
        return self.add(ThresholdConfigModel(
            namespace=namespace,
            index_version=index_version,
            threshold=threshold,
            updated_by=updated_by,
        ))
