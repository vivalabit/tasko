"""make AI persistence and provenance backend-neutral

Revision ID: 20260722_0011
Revises: 20260722_0010
Create Date: 2026-07-22 16:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_0011"
down_revision: str | None = "20260722_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("candidate_match_snapshots") as batch_op:
        batch_op.alter_column(
            "openclaw_error",
            new_column_name="provider_error",
            existing_type=sa.String(length=240),
            existing_nullable=True,
        )
    with op.batch_alter_table("job_matches") as batch_op:
        batch_op.alter_column(
            "openclaw_error",
            new_column_name="provider_error",
            existing_type=sa.String(length=240),
            existing_nullable=True,
        )
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column(
            "openclaw_session_key",
            new_column_name="provider_session_id",
            existing_type=sa.String(length=500),
            existing_nullable=True,
        )

    op.execute(
        sa.text(
            "UPDATE candidate_match_snapshots "
            "SET source = 'openclaw_codex' WHERE source = 'openclaw'"
        )
    )
    op.execute(
        sa.text("UPDATE job_matches SET source = 'openclaw_codex' WHERE source = 'openclaw'")
    )
    op.execute(
        sa.text("UPDATE messages SET source = 'openclaw_codex' WHERE source = 'openclaw'")
    )

    op.add_column(
        "job_matches",
        sa.Column(
            "backend",
            sa.String(length=32),
            nullable=False,
            server_default="openclaw_codex",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE job_matches SET backend = CASE "
            "WHEN source IN ('openclaw_codex', 'openai_api', 'local') THEN source "
            "ELSE 'local' END"
        )
    )
    with op.batch_alter_table("job_matches") as batch_op:
        batch_op.alter_column(
            "backend",
            existing_type=sa.String(length=32),
            nullable=False,
            server_default=None,
        )
        batch_op.create_index(op.f("ix_job_matches_backend"), ["backend"], unique=False)

    for table_name in (
        "document_generation_provenance",
        "document_version_generation_provenance",
        "document_generation_artifacts",
    ):
        op.add_column(
            table_name,
            sa.Column(
                "generation_backend",
                sa.String(length=32),
                nullable=False,
                server_default="openclaw_codex",
            ),
        )
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                "generation_backend",
                existing_type=sa.String(length=32),
                nullable=False,
                server_default=None,
            )


def downgrade() -> None:
    for table_name in (
        "document_generation_artifacts",
        "document_version_generation_provenance",
        "document_generation_provenance",
    ):
        op.drop_column(table_name, "generation_backend")

    with op.batch_alter_table("job_matches") as batch_op:
        batch_op.drop_index(op.f("ix_job_matches_backend"))
        batch_op.drop_column("backend")

    op.execute(
        sa.text(
            "UPDATE candidate_match_snapshots "
            "SET source = 'openclaw' WHERE source = 'openclaw_codex'"
        )
    )
    op.execute(
        sa.text("UPDATE job_matches SET source = 'openclaw' WHERE source = 'openclaw_codex'")
    )
    op.execute(
        sa.text("UPDATE messages SET source = 'openclaw' WHERE source = 'openclaw_codex'")
    )

    with op.batch_alter_table("conversations") as batch_op:
        batch_op.alter_column(
            "provider_session_id",
            new_column_name="openclaw_session_key",
            existing_type=sa.String(length=500),
            existing_nullable=True,
        )
    with op.batch_alter_table("job_matches") as batch_op:
        batch_op.alter_column(
            "provider_error",
            new_column_name="openclaw_error",
            existing_type=sa.String(length=240),
            existing_nullable=True,
        )
    with op.batch_alter_table("candidate_match_snapshots") as batch_op:
        batch_op.alter_column(
            "provider_error",
            new_column_name="openclaw_error",
            existing_type=sa.String(length=240),
            existing_nullable=True,
        )
