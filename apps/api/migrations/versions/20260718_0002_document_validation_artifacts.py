"""add one-time document validation artifacts

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_validation_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=160), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("template_hash", sa.String(length=64), nullable=False),
        sa.Column("result_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_hash", sa.String(length=64), nullable=False),
        sa.Column("rendered_hash", sa.String(length=64), nullable=False),
        sa.Column("rendered_content", sa.LargeBinary(), nullable=False),
        sa.Column("validation_report", sa.JSON(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_validation_artifacts_application_id"),
        "document_validation_artifacts",
        ["application_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_document_validation_artifacts_application_id"),
        table_name="document_validation_artifacts",
    )
    op.drop_table("document_validation_artifacts")
