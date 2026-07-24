"""store source search config provenance on imported jobs

Revision ID: 20260724_0019
Revises: 20260724_0018
Create Date: 2026-07-24 18:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0019"
down_revision: str | None = "20260724_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "stored_jobs",
        sa.Column("search_config_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "stored_jobs",
        sa.Column(
            "search_config_version",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "stored_jobs",
        sa.Column(
            "screening_config_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )
    op.add_column(
        "stored_jobs",
        sa.Column("screening_config_snapshot", sa.JSON(), nullable=True),
    )
    op.create_index(
        op.f("ix_stored_jobs_search_config_id"),
        "stored_jobs",
        ["search_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stored_jobs_screening_config_hash"),
        "stored_jobs",
        ["screening_config_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_stored_jobs_screening_config_hash"),
        table_name="stored_jobs",
    )
    op.drop_index(
        op.f("ix_stored_jobs_search_config_id"),
        table_name="stored_jobs",
    )
    op.drop_column("stored_jobs", "screening_config_snapshot")
    op.drop_column("stored_jobs", "screening_config_hash")
    op.drop_column("stored_jobs", "search_config_version")
    op.drop_column("stored_jobs", "search_config_id")
