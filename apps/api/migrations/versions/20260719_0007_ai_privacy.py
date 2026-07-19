"""persist AI consent and retention settings

Revision ID: 20260719_0007
Revises: 20260719_0006
Create Date: 2026-07-19 17:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_0007"
down_revision: str | None = "20260719_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_OWNER_ID = "local-owner"
AI_OWNER_TABLES = (
    "conversations",
    "applied_assistant_actions",
    "job_matches",
    "candidate_match_snapshots",
)


def upgrade() -> None:
    for table_name in AI_OWNER_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "owner_id",
                sa.String(length=160),
                nullable=False,
                server_default=LEGACY_OWNER_ID,
            ),
        )
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                "owner_id",
                existing_type=sa.String(length=160),
                nullable=False,
                server_default=None,
            )
            batch_op.create_index(
                op.f(f"ix_{table_name}_owner_id"),
                ["owner_id"],
                unique=False,
            )

    op.create_table(
        "ai_privacy_settings",
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.Column("consent_version", sa.String(length=80), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("last_ai_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_data_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("owner_id"),
    )
    op.create_index(
        op.f("ix_ai_privacy_settings_ai_data_expires_at"),
        "ai_privacy_settings",
        ["ai_data_expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ai_privacy_settings_ai_data_expires_at"),
        table_name="ai_privacy_settings",
    )
    op.drop_table("ai_privacy_settings")

    for table_name in reversed(AI_OWNER_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(op.f(f"ix_{table_name}_owner_id"))
            batch_op.drop_column("owner_id")
