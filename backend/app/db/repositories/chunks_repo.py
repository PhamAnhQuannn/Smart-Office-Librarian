"""Chunk metadata persistence repository."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ChunkModel
from app.db.repositories.base_repo import BaseRepository


class ChunksRepository(BaseRepository[ChunkModel]):
    model_class = ChunkModel

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def get_by_vector_id(self, vector_id: str) -> ChunkModel | None:
        stmt = select(ChunkModel).where(ChunkModel.vector_id == vector_id)
        return self._session.scalars(stmt).first()

    def list_by_source(self, source_id: str) -> list[ChunkModel]:
        stmt = select(ChunkModel).where(ChunkModel.source_id == source_id)
        return list(self._session.scalars(stmt))

    def get_by_simhash(self, simhash: str) -> ChunkModel | None:
        stmt = select(ChunkModel).where(ChunkModel.simhash == simhash)
        return self._session.scalars(stmt).first()

    def create(self, *, source_id: str, vector_id: str, text: str, namespace: str,
               simhash: str | None = None, start_line: int | None = None,
               end_line: int | None = None) -> ChunkModel:
        chunk = ChunkModel(
            source_id=source_id,
            vector_id=vector_id,
            text=text,
            namespace=namespace,
            simhash=simhash,
            start_line=start_line,
            end_line=end_line,
        )
        return self.add(chunk)

    def delete_by_source(self, source_id: str) -> int:
        chunks = self.list_by_source(source_id)
        for chunk in chunks:
            self._session.delete(chunk)
        self._session.flush()
        return len(chunks)

    def count_by_namespace(self, namespace: str) -> int:
        """Return total number of chunks for a given Pinecone namespace (= workspace slug)."""
        stmt = select(func.count()).select_from(ChunkModel).where(
            ChunkModel.namespace == namespace
        )
        return self._session.scalar(stmt) or 0
