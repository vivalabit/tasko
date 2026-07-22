"""preserve dismissed jobs as search tombstones

Revision ID: 20260722_0010
Revises: 20260720_0009
Create Date: 2026-07-22 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_0010"
down_revision: str | None = "20260720_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stored_jobs",
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "stored_jobs",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_stored_jobs_status"),
        "stored_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stored_jobs_status"), table_name="stored_jobs")
    op.drop_column("stored_jobs", "dismissed_at")
    op.drop_column("stored_jobs", "status")
