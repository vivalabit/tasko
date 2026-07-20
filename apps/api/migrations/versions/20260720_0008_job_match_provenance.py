"""persist complete job-match provenance

Revision ID: 20260720_0008
Revises: 20260719_0007
Create Date: 2026-07-20 10:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260720_0008"
down_revision: str | None = "20260719_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows cannot prove these inputs and must remain non-authoritative.
    for name, length in (
        ("vacancy_hash", 64),
        ("model", 160),
        ("prompt_version", 64),
    ):
        op.add_column(
            "job_matches",
            sa.Column(name, sa.String(length=length), nullable=False, server_default=""),
        )
        with op.batch_alter_table("job_matches") as batch_op:
            batch_op.alter_column(
                name,
                existing_type=sa.String(length=length),
                nullable=False,
                server_default=None,
            )
            batch_op.create_index(
                op.f(f"ix_job_matches_{name}"),
                [name],
                unique=False,
            )


def downgrade() -> None:
    for name in ("prompt_version", "model", "vacancy_hash"):
        with op.batch_alter_table("job_matches") as batch_op:
            batch_op.drop_index(op.f(f"ix_job_matches_{name}"))
            batch_op.drop_column(name)
