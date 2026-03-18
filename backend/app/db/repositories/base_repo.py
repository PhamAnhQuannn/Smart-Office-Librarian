"""Generic base repository with common CRUD helpers."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Provides get, list, add, and delete for a single model class."""

    model_class: type

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, record_id: str) -> T | None:
        return self._session.get(self.model_class, record_id)

    def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:
        stmt = select(self.model_class).offset(offset).limit(limit)
        return list(self._session.scalars(stmt))

    def add(self, obj: T) -> T:
        self._session.add(obj)
        self._session.flush()
        return obj

    def delete(self, obj: T) -> None:
        self._session.delete(obj)
        self._session.flush()
