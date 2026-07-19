"""persist workspace source documents

Revision ID: 20260719_0004
Revises: 20260718_0003
Create Date: 2026-07-19 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260719_0004"
down_revision: str | None = "20260718_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_source_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("file_name", sa.String(length=240), nullable=False),
        sa.Column("content_type", sa.String(length=160), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["stored_applications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workspace_source_documents_application_id"),
        "workspace_source_documents",
        ["application_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_workspace_source_documents_updated_at"),
        "workspace_source_documents",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_workspace_source_documents_updated_at"),
        table_name="workspace_source_documents",
    )
    op.drop_index(
        op.f("ix_workspace_source_documents_application_id"),
        table_name="workspace_source_documents",
    )
    op.drop_table("workspace_source_documents")
