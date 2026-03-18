"""Retrieval stage: embed query → vector search → rerank.

Contract:
  Input:  query_text, rbac_filter, namespace
  Output: dict with ranked_sources, primary_cosine_score, cache_hit, latency_ms
          (matches RetrievalResult.as_dict())
"""

from __future__ import annotations

import time
from typing import Any

from app.rag.retrieval.cache_keys import query_result_key


class RetrievalStage:
    """Orchestrates embedding, vector search, and reranking."""

    def __init__(
        self,
        *,
        embedder: Any,
        vector_store: Any,
        reranker: Any,
        cache: Any | None = None,
        top_k: int = 10,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._reranker = reranker
        self._cache = cache
        self._top_k = top_k

    def run(
        self,
        *,
        query_text: str,
        rbac_filter: dict[str, Any] | None,
        namespace: str,
    ) -> dict[str, Any]:
        start = time.perf_counter()

        # 1. Check query-result cache
        if self._cache is not None:
            cache_key = query_result_key(query_text, namespace, self._top_k)
            cached = self._cache.get(cache_key)
            if cached is not None:
                cached["cache_hit"] = True
                cached["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
                return cached

        # 2. Embed the query
        vector = self._embedder.embed(query_text)

        # 3. Vector store similarity search
        hits = self._vector_store.query(
            vector,
            top_k=self._top_k,
            namespace=namespace,
            filter=rbac_filter,
        )

        # 4. Rerank (score floor + top-k)
        ranked = self._reranker.rerank(hits)

        primary_score = ranked[0]["score"] if ranked else 0.0
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        result: dict[str, Any] = {
            "ranked_sources": ranked,
            "primary_cosine_score": primary_score,
            "cache_hit": False,
            "latency_ms": latency_ms,
        }

        # 5. Store in cache
        if self._cache is not None:
            self._cache.set(cache_key, result)  # type: ignore[possibly-undefined]

        return result
