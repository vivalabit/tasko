"""bind AI consent to the selected backend

Revision ID: 20260722_0013
Revises: 20260722_0012
Create Date: 2026-07-22 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_0013"
down_revision: str | None = "20260722_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_privacy_settings",
        sa.Column("consent_backend", sa.String(length=32), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE ai_privacy_settings SET consent_backend = 'openclaw_codex' "
            "WHERE consented_at IS NOT NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("ai_privacy_settings", "consent_backend")
