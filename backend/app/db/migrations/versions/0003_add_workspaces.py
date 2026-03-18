"""Add workspaces table; workspace_id FK on sources + ingest_runs; drop sources.visibility.

Revision ID: 0003_add_workspaces
Revises: 0002_fix_sources_schema
Create Date: 2026-03-17 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_workspaces"
down_revision: Union[str, None] = "0002_fix_sources_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── workspaces ─────────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("owner_id", sa.String(36), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("max_chunks", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column("max_sources", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("monthly_query_cap", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # ── sources: add workspace_id, drop visibility ─────────────────────────────
    # Use IF NOT EXISTS to handle re-runs or partial prior migrations
    op.execute("ALTER TABLE sources ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(36)")
    op.execute("ALTER TABLE sources ADD COLUMN IF NOT EXISTS last_indexed_sha VARCHAR(40)")

    # Back-fill: leave workspace_id NULL for now (existing rows from old schema)
    # Operators must re-ingest after migration on live systems with existing data.

    # Create FK only if it doesn't already exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_sources_workspace_id'
            ) THEN
                ALTER TABLE sources
                    ADD CONSTRAINT fk_sources_workspace_id
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sources_workspace_id ON sources (workspace_id)
    """)

    # Drop old visibility column (workspace namespace is the isolation mechanism now)
    op.execute("ALTER TABLE sources DROP COLUMN IF EXISTS visibility")

    # ── ingest_runs: add workspace_id ──────────────────────────────────────────
    op.execute("ALTER TABLE ingest_runs ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(36)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ingest_runs_workspace_id_fkey'
            ) THEN
                ALTER TABLE ingest_runs
                    ADD CONSTRAINT ingest_runs_workspace_id_fkey
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("ingest_runs", "workspace_id")

    op.drop_index("ix_sources_workspace_id", table_name="sources")
    op.drop_constraint("fk_sources_workspace_id", "sources", type_="foreignkey")
    op.drop_column("sources", "workspace_id")
    op.drop_column("sources", "last_indexed_sha")
    op.add_column(
        "sources",
        sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
    )

    op.drop_index("ix_workspaces_owner_id", table_name="workspaces")
    op.drop_table("workspaces")
