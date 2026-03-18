"""Cache key builders for the retrieval layer."""

from __future__ import annotations

import hashlib


def embedding_key(text: str, model: str) -> str:
    """Stable cache key for an embedding vector."""
    digest = hashlib.sha256(f"{model}:{text}".encode()).hexdigest()[:32]
    return f"embed:{model}:{digest}"


def query_result_key(query_text: str, namespace: str, top_k: int) -> str:
    """Stable cache key for a vector-store query result."""
    payload = f"{namespace}:{top_k}:{query_text}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return f"qresult:{namespace}:{digest}"
