"""persist job search run warnings

Revision ID: 20260724_0017
Revises: 20260724_0016
Create Date: 2026-07-24 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0017"
down_revision: str | None = "20260724_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job_search_runs",
        sa.Column("warning", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job_search_runs", "warning")
