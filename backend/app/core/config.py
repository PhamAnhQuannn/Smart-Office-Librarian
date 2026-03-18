"""Application configuration resolved from environment variables.

All settings are read once at first access and cached in a module-level
singleton.  Use ``get_settings()`` everywhere; call ``reset_settings()``
in tests to force re-evaluation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    return int(raw) if raw else default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    return float(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    # ── Database ──────────────────────────────────────────────────────────────
    db_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            "postgresql+psycopg://embedlyzer:embedlyzer@localhost:5432/embedlyzer",
        )
    )
    db_pool_size: int = field(default_factory=lambda: _env_int("DB_POOL_SIZE", 5))
    db_max_overflow: int = field(default_factory=lambda: _env_int("DB_MAX_OVERFLOW", 10))

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = field(
        default_factory=lambda: _env("REDIS_URL", "redis://localhost:6379/0")
    )
    redis_ttl_seconds: int = field(
        default_factory=lambda: _env_int("REDIS_TTL_SECONDS", 3600)
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str = field(
        default_factory=lambda: _env("OPENAI_API_KEY")
    )
    openai_embedding_model: str = field(
        default_factory=lambda: _env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    )
    openai_chat_model: str = field(
        default_factory=lambda: _env("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    )
    openai_max_tokens: int = field(
        default_factory=lambda: _env_int("OPENAI_MAX_TOKENS", 1024)
    )
    openai_temperature: float = field(
        default_factory=lambda: _env_float("OPENAI_TEMPERATURE", 0.0)
    )

    # ── Pinecone ──────────────────────────────────────────────────────────────
    pinecone_api_key: str = field(
        default_factory=lambda: _env("PINECONE_API_KEY")
    )
    pinecone_index_name: str = field(
        default_factory=lambda: _env("PINECONE_INDEX_NAME", "embedlyzer")
    )

    # ── Authentication ────────────────────────────────────────────────────────
    jwt_secret: str = field(
        default_factory=lambda: _env("JWT_SECRET")
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = field(
        default_factory=lambda: _env("APP_ENV", "development")
    )
    log_level: str = field(
        default_factory=lambda: _env("LOG_LEVEL", "INFO")
    )

    # ── RAG behaviour ─────────────────────────────────────────────────────────
    default_threshold: float = field(
        default_factory=lambda: _env_float("DEFAULT_THRESHOLD", 0.75)
    )
    default_namespace: str = field(
        default_factory=lambda: _env("DEFAULT_NAMESPACE", "dev")
    )
    max_context_chunks: int = field(
        default_factory=lambda: _env_int("MAX_CONTEXT_CHUNKS", 5)
    )
    embedding_cache_ttl_seconds: int = field(
        default_factory=lambda: _env_int("EMBEDDING_CACHE_TTL_SECONDS", 86400)
    )

    # ── GitHub connector ──────────────────────────────────────────────────────
    github_token: str = field(
        default_factory=lambda: _env("GITHUB_TOKEN")
    )

    # ── Budget / cost control ─────────────────────────────────────────────────
    monthly_token_budget: int = field(
        default_factory=lambda: _env_int("MONTHLY_TOKEN_BUDGET", 1_000_000)
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Discard cached settings — call in tests that mutate env vars."""
    global _settings
    _settings = None
