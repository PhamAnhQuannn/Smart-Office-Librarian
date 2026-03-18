"""Unit tests for app.core.config."""
from __future__ import annotations

import os

import pytest

from app.core.config import Settings, get_settings, reset_settings


def test_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings uses documented defaults when env vars are absent."""
    for key in [
        "DATABASE_URL", "REDIS_URL", "OPENAI_API_KEY",
        "PINECONE_API_KEY", "PINECONE_INDEX_NAME",
        "JWT_SECRET", "APP_ENV", "DEFAULT_THRESHOLD",
        "MAX_CONTEXT_CHUNKS", "MONTHLY_TOKEN_BUDGET",
    ]:
        monkeypatch.delenv(key, raising=False)
    reset_settings()

    s = get_settings()
    assert s.app_env == "development"
    assert 0.0 < s.default_threshold <= 1.0
    assert s.max_context_chunks > 0
    assert s.monthly_token_budget > 0


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables are respected."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEFAULT_THRESHOLD", "0.82")
    monkeypatch.setenv("MAX_CONTEXT_CHUNKS", "7")
    reset_settings()

    s = get_settings()
    assert s.app_env == "production"
    assert abs(s.default_threshold - 0.82) < 1e-6
    assert s.max_context_chunks == 7


def test_singleton_behaviour() -> None:
    """get_settings() returns the same object on repeated calls."""
    a = get_settings()
    b = get_settings()
    assert a is b


def test_reset_re_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """reset_settings() forces a fresh read on the next call."""
    monkeypatch.setenv("APP_ENV", "staging")
    reset_settings()
    s = get_settings()
    assert s.app_env == "staging"


def test_settings_is_frozen() -> None:
    """Settings dataclass must be immutable."""
    s = get_settings()
    with pytest.raises((AttributeError, TypeError)):
        s.app_env = "mutated"  # type: ignore[misc]
