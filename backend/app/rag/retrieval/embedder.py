"""OpenAI embedding wrapper with Redis caching.

Used by the retrieval stage to convert query text into a vector.
Caching is best-effort: failures fall through to the API call.
"""

from __future__ import annotations

import logging
from typing import Any

from app.rag.retrieval.cache_keys import embedding_key

logger = logging.getLogger(__name__)


class Embedder:
    """Wraps the OpenAI embeddings API with an optional Redis cache."""

    def __init__(
        self,
        *,
        openai_client: Any,
        model: str = "text-embedding-3-small",
        cache: Any | None = None,
        ttl_seconds: int = 86400,
    ) -> None:
        self._client = openai_client
        self._model = model
        self._cache = cache
        self._ttl = ttl_seconds

    def embed(self, text: str) -> list[float]:
        """Return the embedding vector for *text*, using cache if available."""
        key = embedding_key(text, self._model)

        if self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                logger.debug("embedding cache hit key=%s", key)
                return cached

        logger.debug("embedding cache miss — calling OpenAI model=%s", self._model)
        response = self._client.embeddings.create(input=text, model=self._model)
        vector: list[float] = response.data[0].embedding

        if self._cache is not None:
            self._cache.set(key, vector, ttl_seconds=self._ttl)

        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single API call."""
        response = self._client.embeddings.create(input=texts, model=self._model)
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
