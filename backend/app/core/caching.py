"""Redis caching abstraction.

``RedisCache`` wraps a redis.Redis client and exposes typed get/set/delete
operations with configurable TTLs.  When Redis is unavailable the methods
degrade gracefully (return None / False) so the application continues to
function without caching.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MISS = object()  # sentinel for cache-miss in get_or_set


class RedisCache:
    """Thin wrapper around a redis.Redis client."""

    def __init__(self, client: Any, *, default_ttl_seconds: int = 3600) -> None:
        """
        Args:
            client: A ``redis.Redis`` (or ``redis.asyncio.Redis``) instance,
                    or any object with .get / .setex / .delete methods.
            default_ttl_seconds: TTL used when callers do not specify one.
        """
        self._client = client
        self._default_ttl = default_ttl_seconds

    # ── read ──────────────────────────────────────────────────────────────────

    def get(self, key: str) -> Any | None:
        """Return the deserialized value or *None* on miss / error."""
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.get failed key=%s error=%s", key, exc)
            return None

    # ── write ─────────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any, *, ttl_seconds: int | None = None) -> bool:
        """Serialize and store *value*.  Returns True on success."""
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        try:
            serialized = json.dumps(value)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.set failed key=%s error=%s", key, exc)
            return False

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, key: str) -> bool:
        """Remove key.  Returns True if key existed."""
        try:
            return bool(self._client.delete(key))
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.delete failed key=%s error=%s", key, exc)
            return False

    # ── utils ─────────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True when Redis responds to PING."""
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001
            return False


def build_embedding_cache_key(text: str, model: str) -> str:
    """Deterministic cache key for an embedding."""
    import hashlib

    digest = hashlib.sha256(f"{model}:{text}".encode()).hexdigest()[:32]
    return f"embed:{model}:{digest}"


def build_query_cache_key(query_text: str, namespace: str, threshold: float) -> str:
    """Deterministic cache key for a full RAG result."""
    import hashlib

    payload = f"{namespace}:{threshold}:{query_text}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return f"query:{namespace}:{digest}"
