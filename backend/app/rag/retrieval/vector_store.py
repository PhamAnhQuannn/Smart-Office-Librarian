"""Pinecone vector store wrapper.

Handles index initialisation, namespace-aware upsert and similarity query.
Returns hits as plain dicts compatible with the rest of the pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VectorStore:
    """Wraps a Pinecone index for upsert and query operations."""

    def __init__(self, *, index: Any, default_namespace: str = "dev") -> None:
        self._index = index
        self._default_namespace = default_namespace

    # ── write ─────────────────────────────────────────────────────────────────

    def upsert(
        self,
        vectors: list[dict[str, Any]],
        *,
        namespace: str | None = None,
    ) -> None:
        """Insert or update vectors in the specified namespace.

        Each vector dict must contain: id (str), values (list[float]),
        and optionally metadata (dict).
        """
        ns = namespace or self._default_namespace
        self._index.upsert(vectors=vectors, namespace=ns)
        logger.debug("upserted %d vectors to namespace=%s", len(vectors), ns)

    def delete(self, vector_ids: list[str], *, namespace: str | None = None) -> None:
        """Delete vectors by ID from the specified namespace."""
        ns = namespace or self._default_namespace
        self._index.delete(ids=vector_ids, namespace=ns)
        logger.debug("deleted %d vectors from namespace=%s", len(vector_ids), ns)

    # ── query ─────────────────────────────────────────────────────────────────

    def query(
        self,
        vector: list[float],
        *,
        top_k: int = 10,
        namespace: str | None = None,
        filter: dict[str, Any] | None = None,
        include_metadata: bool = True,
    ) -> list[dict[str, Any]]:
        """Similarity search.  Returns a list of hit dicts sorted by score desc.

        Each hit dict has keys: id, score, metadata.
        """
        ns = namespace or self._default_namespace
        response = self._index.query(
            vector=vector,
            top_k=top_k,
            namespace=ns,
            filter=filter,
            include_metadata=include_metadata,
            include_values=False,
        )
        hits = []
        for match in response.matches:
            meta = match.metadata or {}
            hits.append({
                "vector_id": match.id,
                "score": float(match.score),
                "text": meta.get("text", ""),
                "file_path": meta.get("file_path", ""),
                "source_url": meta.get("source_url"),
                "start_line": meta.get("start_line"),
                "end_line": meta.get("end_line"),
                "namespace": ns,
            })
        logger.debug(
            "vector store query top_k=%d namespace=%s hits=%d", top_k, ns, len(hits)
        )
        return hits

    # ── health ─────────────────────────────────────────────────────────────────

    def describe_index_stats(self) -> dict[str, Any]:
        """Return vector count and other index metadata."""
        return dict(self._index.describe_index_stats())
