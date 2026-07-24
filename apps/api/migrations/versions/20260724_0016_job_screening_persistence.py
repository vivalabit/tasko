"""persist job screening decisions and expanded run statistics

Revision ID: 20260724_0016
Revises: 20260723_0015
Create Date: 2026-07-24 14:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_0016"
down_revision: str | None = "20260723_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RUN_STAT_COLUMNS = (
    "jobs_already_known",
    "jobs_screened",
    "jobs_passed",
    "jobs_rejected",
    "jobs_uncertain",
    "jobs_analyzed",
    "screening_errors",
)


def upgrade() -> None:
    op.create_table(
        "job_screening_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_hash", sa.String(length=64), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("matched_rule_ids", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("company", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "decision IN ('keep', 'reject', 'uncertain')",
            name="ck_job_screening_decisions_decision",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "vacancy_hash",
        "config_hash",
        "decision",
        "model",
        "prompt_version",
        "created_at",
        "owner_id",
    ):
        op.create_index(
            op.f(f"ix_job_screening_decisions_{column}"),
            "job_screening_decisions",
            [column],
            unique=False,
        )
    op.create_index(
        "ix_job_screening_decisions_cache",
        "job_screening_decisions",
        [
            "owner_id",
            "vacancy_hash",
            "config_hash",
            "model",
            "prompt_version",
        ],
        unique=False,
    )

    with op.batch_alter_table("job_search_runs") as batch_op:
        for column in RUN_STAT_COLUMNS:
            batch_op.add_column(
                sa.Column(
                    column,
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                )
            )
    op.execute(
        sa.text(
            "UPDATE job_search_runs SET jobs_already_known = "
            "CASE WHEN jobs_found > jobs_added "
            "THEN jobs_found - jobs_added ELSE 0 END"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("job_search_runs") as batch_op:
        for column in reversed(RUN_STAT_COLUMNS):
            batch_op.drop_column(column)

    op.drop_index(
        "ix_job_screening_decisions_cache",
        table_name="job_screening_decisions",
    )
    op.drop_table("job_screening_decisions")
