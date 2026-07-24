"""add actionable vacancy screening audit metadata

Revision ID: 20260724_0018
Revises: 20260724_0017
Create Date: 2026-07-24 16:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0018"
down_revision: str | None = "20260724_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_screening_decisions",
        sa.Column(
            "job_id",
            sa.String(length=160),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "job_screening_decisions",
        sa.Column("search_config_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "job_screening_decisions",
        sa.Column(
            "vacancy_data",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column(
        "job_screening_decisions",
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "job_screening_decisions",
        sa.Column(
            "manually_allowed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_job_screening_decisions_job_id"),
        "job_screening_decisions",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_screening_decisions_search_config_id"),
        "job_screening_decisions",
        ["search_config_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_job_screening_decisions_search_config_id"),
        table_name="job_screening_decisions",
    )
    op.drop_index(
        op.f("ix_job_screening_decisions_job_id"),
        table_name="job_screening_decisions",
    )
    op.drop_column("job_screening_decisions", "manually_allowed_at")
    op.drop_column("job_screening_decisions", "invalidated_at")
    op.drop_column("job_screening_decisions", "vacancy_data")
    op.drop_column("job_screening_decisions", "search_config_id")
    op.drop_column("job_screening_decisions", "job_id")
