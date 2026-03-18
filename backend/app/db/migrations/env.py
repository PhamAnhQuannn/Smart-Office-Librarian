"""Alembic environment configuration."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the metadata from our ORM models so Alembic can detect schema changes.
from app.db.base import Base
import app.db.models  # noqa: F401 — registers all ORM models on Base.metadata

# Alembic Config object provides access to values in alembic.ini.
config = context.config

# Configure Python logging from alembic.ini (if present).
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

# Metadata object used for 'autogenerate' support.
target_metadata = Base.metadata


def _get_url() -> str:
    """Return the DB URL: prefer DATABASE_URL env var over alembic.ini setting."""
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("DB_URL")
        or config.get_main_option("sqlalchemy.url", "postgresql+psycopg://localhost/embedlyzer")
    )


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
