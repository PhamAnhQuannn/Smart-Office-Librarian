"""Fix sources table: replace branch/namespace/index_version with file_path/source_url.

Revision ID: 0002_fix_sources_schema
Revises: 0001_initial_schema
Create Date: 2026-01-02 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_fix_sources_schema"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop columns that are in the migration but not in the ORM model
    op.drop_index("ix_sources_repo_branch", table_name="sources")
    op.drop_column("sources", "branch")
    op.drop_column("sources", "namespace")
    op.drop_column("sources", "index_version")

    # Add columns that the ORM model expects
    # Use server_default='' temporarily so existing rows (if any) satisfy NOT NULL
    op.add_column("sources", sa.Column("file_path", sa.String(1024), nullable=True))
    op.add_column("sources", sa.Column("source_url", sa.String(2048), nullable=True))

    # Back-fill any pre-existing rows so we can enforce NOT NULL
    op.execute("UPDATE sources SET file_path = '' WHERE file_path IS NULL")
    op.alter_column("sources", "file_path", nullable=False)

    # Composite index matching the query in sources_repo.py
    op.create_index("ix_sources_repo_file_path", "sources", ["repo", "file_path"])


def downgrade() -> None:
    op.drop_index("ix_sources_repo_file_path", table_name="sources")
    op.drop_column("sources", "file_path")
    op.drop_column("sources", "source_url")

    op.add_column("sources", sa.Column("branch", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("namespace", sa.Text(), nullable=True))
    op.add_column(
        "sources",
        sa.Column("index_version", sa.Integer(), nullable=True),
    )
    op.execute("UPDATE sources SET branch = 'main', namespace = 'dev', index_version = 1")
    op.alter_column("sources", "branch", nullable=False)
    op.alter_column("sources", "namespace", nullable=False)
    op.alter_column("sources", "index_version", nullable=False)
    op.create_index("ix_sources_repo_branch", "sources", ["repo", "branch"])
