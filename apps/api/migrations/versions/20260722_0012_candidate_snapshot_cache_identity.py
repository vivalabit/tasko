"""key candidate snapshot cache by backend and model

Revision ID: 20260722_0012
Revises: 20260722_0011
Create Date: 2026-07-22 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_0012"
down_revision: str | None = "20260722_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_match_snapshots",
        sa.Column("model", sa.String(length=160), nullable=False, server_default="legacy"),
    )
    op.execute(
        sa.text(
            "UPDATE candidate_match_snapshots SET model = 'local' WHERE source = 'local'"
        )
    )
    with op.batch_alter_table("candidate_match_snapshots") as batch_op:
        batch_op.alter_column(
            "model",
            existing_type=sa.String(length=160),
            nullable=False,
            server_default=None,
        )
        batch_op.create_index(
            "ix_candidate_match_snapshots_cache_identity",
            ["profile_input_hash", "matcher_version", "source", "model"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_match_snapshots") as batch_op:
        batch_op.drop_index("ix_candidate_match_snapshots_cache_identity")
        batch_op.drop_column("model")
