"""Make hashed_password nullable to support Google OAuth users.

Revision ID: 0004_google_oauth
Revises: 0003_add_workspaces
Create Date: 2026-03-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0004_google_oauth"
down_revision: str | None = "0003_add_workspaces"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Clear nulls before restoring NOT NULL constraint (Google-only accounts would lose access)
    op.execute("UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
