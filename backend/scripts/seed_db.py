#!/usr/bin/env python
"""Seed development database with an admin user and sample data.

Usage (from backend/):
    python scripts/seed_db.py [--reset] [--admin-email EMAIL] [--admin-password PASSWORD]

Credentials are resolved in priority order:
    1. CLI flags (--admin-email / --admin-password)
    2. Environment variables (SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD)
    3. Defaults (admin@example.com / changeme123!) — DEV ONLY, never use in production.

Options:
    --reset              Drop and recreate all tables before seeding (DEV ONLY).
    --admin-email EMAIL  Email for the initial admin account.
    --admin-password PW  Password for the initial admin account.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone

# Ensure backend package on path when executed directly.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import (
    FeedbackModel,
    IngestRunModel,
    QueryLogModel,
    SourceModel,
    UserModel,
    WorkspaceModel,
)
from app.db.session import get_engine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


def _hash_password(plain: str) -> str:
    """Minimal bcrypt hash — requires `passlib[bcrypt]` in the environment."""
    try:
        from passlib.context import CryptContext  # type: ignore[import]
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(plain)
    except ImportError:
        # Fallback: clearly-invalid hash so the app won't accept logins in prod.
        return f"INSECURE-PLAIN:{plain}"


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_DEFAULT_ADMIN_EMAIL = "admin@example.com"
_DEFAULT_ADMIN_PASSWORD = "changeme123!"

SAMPLE_SOURCES = [
    {
        "repo": "acme-org/docs",
        "file_path": "README.md",
        "source_url": "https://github.com/acme-org/docs/blob/main/README.md",
    },
    {
        "repo": "acme-org/docs",
        "file_path": "architecture/overview.md",
        "source_url": "https://github.com/acme-org/docs/blob/main/architecture/overview.md",
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed(
    reset: bool = False,
    admin_email: str | None = None,
    admin_password: str | None = None,
) -> None:
    # Resolve credentials: CLI arg > env var > insecure default
    effective_email = (
        admin_email
        or os.environ.get("SEED_ADMIN_EMAIL")
        or _DEFAULT_ADMIN_EMAIL
    )
    effective_password = (
        admin_password
        or os.environ.get("SEED_ADMIN_PASSWORD")
        or _DEFAULT_ADMIN_PASSWORD
    )
    if effective_email == _DEFAULT_ADMIN_EMAIL or effective_password == _DEFAULT_ADMIN_PASSWORD:
        print(
            "WARNING: Using default seed credentials. "
            "Set SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD env vars or pass --admin-email / --admin-password."
        )

    settings = get_settings()
    engine = get_engine()

    if reset:
        print("⚠  --reset: dropping all tables …")
        Base.metadata.drop_all(engine)
        print("   Tables dropped.")

    Base.metadata.create_all(engine)
    print("✓  Schema up-to-date.")

    from sqlalchemy.orm import Session

    with Session(engine) as session:
        # ── Admin user ──────────────────────────────────────────────────────
        existing = session.query(UserModel).filter_by(email=effective_email).first()
        if existing:
            print(f"   Admin user already exists: {effective_email}")
            admin_id = existing.id
        else:
            admin_id = _uuid()
            admin = UserModel(
                id=admin_id,
                email=effective_email,
                hashed_password=_hash_password(effective_password),
                role="admin",
                is_active=True,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            session.add(admin)
            print(f"✓  Created admin user: {effective_email}")

        # ── Admin workspace ──────────────────────────────────────────────────
        existing_ws = session.query(WorkspaceModel).filter_by(owner_id=admin_id).first()
        if existing_ws:
            print(f"   Workspace already exists for admin: {existing_ws.slug}")
            workspace_id = existing_ws.id
            workspace_slug = existing_ws.slug
        else:
            # Derive slug from admin_id (same logic as workspaces_repo)
            raw = admin_id.replace("-", "")[:24].lower()
            workspace_slug = f"ws-{raw}"
            workspace_id = _uuid()
            workspace = WorkspaceModel(
                id=workspace_id,
                owner_id=admin_id,
                slug=workspace_slug,
                display_name="Admin Workspace",
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            session.add(workspace)
            print(f"✓  Created workspace: {workspace_slug}")

        # ── Sample sources ───────────────────────────────────────────────────
        for src_data in SAMPLE_SOURCES:
            existing_src = (
                session.query(SourceModel)
                .filter_by(
                    workspace_id=workspace_id,
                    repo=src_data["repo"],
                    file_path=src_data["file_path"],
                )
                .first()
            )
            if existing_src:
                print(f"   Source already exists: {src_data['file_path']}")
                continue
            source = SourceModel(
                id=_uuid(),
                workspace_id=workspace_id,
                repo=src_data["repo"],
                file_path=src_data["file_path"],
                source_url=src_data.get("source_url"),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            session.add(source)
            print(f"✓  Created source: {src_data['repo']}/{src_data['file_path']}")

        session.commit()

    print("\nSeed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Embedlyzer development database.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first.")
    parser.add_argument(
        "--admin-email",
        default=None,
        help="Email for the initial admin user (overrides SEED_ADMIN_EMAIL env var).",
    )
    parser.add_argument(
        "--admin-password",
        default=None,
        help="Password for the initial admin user (overrides SEED_ADMIN_PASSWORD env var).",
    )
    args = parser.parse_args()
    seed(reset=args.reset, admin_email=args.admin_email, admin_password=args.admin_password)
