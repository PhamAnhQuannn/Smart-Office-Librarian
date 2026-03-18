"""Unit tests for app.core.caching (RedisCache)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.caching import RedisCache, build_embedding_cache_key, build_query_cache_key


# ---------------------------------------------------------------------------
# Fake Redis client
# ---------------------------------------------------------------------------

class _FakeRedis:
    """In-memory dict-backed fake that honours the redis.Redis interface."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def setex(self, key: str, ttl: int, value: bytes) -> None:  # noqa: ARG002
        self._store[key] = value if isinstance(value, bytes) else value.encode()

    def delete(self, *keys: str) -> int:
        removed = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                removed += 1
        return removed

    def ping(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def cache() -> RedisCache:
    return RedisCache(_FakeRedis(), default_ttl_seconds=60)


def test_set_and_get(cache: RedisCache) -> None:
    cache.set("k1", {"hello": "world"})
    assert cache.get("k1") == {"hello": "world"}


def test_get_miss_returns_none(cache: RedisCache) -> None:
    assert cache.get("no-such-key") is None


def test_delete_removes_key(cache: RedisCache) -> None:
    cache.set("k2", [1, 2, 3])
    cache.delete("k2")
    assert cache.get("k2") is None


def test_ping_returns_true(cache: RedisCache) -> None:
    assert cache.ping() is True


def test_get_returns_none_on_redis_error() -> None:
    bad = MagicMock()
    bad.get.side_effect = Exception("connection refused")
    c = RedisCache(bad)
    assert c.get("k") is None


def test_set_tolerates_redis_error() -> None:
    bad = MagicMock()
    bad.setex.side_effect = Exception("connection refused")
    c = RedisCache(bad)
    # Should not raise
    c.set("k", "v")


def test_ping_returns_false_on_error() -> None:
    bad = MagicMock()
    bad.ping.side_effect = Exception("timeout")
    c = RedisCache(bad)
    assert c.ping() is False


def test_embedding_cache_key() -> None:
    key = build_embedding_cache_key("hello world", model="text-embedding-3-small")
    assert isinstance(key, str) and len(key) > 0
    # Same text + model → same key
    assert key == build_embedding_cache_key("hello world", model="text-embedding-3-small")
    # Different text → different key
    assert key != build_embedding_cache_key("different text here", model="text-embedding-3-small")


def test_query_cache_key() -> None:
    key = build_query_cache_key("what is rag?", namespace="default", threshold=0.75)
    assert isinstance(key, str) and len(key) > 0
    assert key == build_query_cache_key("what is rag?", namespace="default", threshold=0.75)
    assert key != build_query_cache_key("another question entirely", namespace="default", threshold=0.75)
