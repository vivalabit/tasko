"""persist automatic job search configuration and run history

Revision ID: 20260723_0015
Revises: 20260723_0014
Create Date: 2026-07-23 13:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0015"
down_revision: str | None = "20260723_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_search_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_search_configs_owner_id"),
        "job_search_configs",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_search_configs_updated_at"),
        "job_search_configs",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "job_search_schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("config_id", sa.String(length=36), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("weekdays", sa.JSON(), nullable=False),
        sa.Column("local_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("ai_analysis_enabled", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["config_id"],
            ["job_search_configs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("config_id", "enabled", "next_run_at", "owner_id"):
        op.create_index(
            op.f(f"ix_job_search_schedules_{column}"),
            "job_search_schedules",
            [column],
            unique=False,
        )
    op.create_index(
        "ix_job_search_schedules_due",
        "job_search_schedules",
        ["enabled", "next_run_at"],
        unique=False,
    )

    op.create_table(
        "job_search_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("schedule_id", sa.String(length=36), nullable=True),
        sa.Column("run_type", sa.String(length=16), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config_snapshot", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False),
        sa.Column("jobs_added", sa.Integer(), nullable=False),
        sa.Column("source_errors", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.CheckConstraint(
            "run_type IN ('manual', 'automatic')",
            name="ck_job_search_runs_run_type",
        ),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["job_search_schedules.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "schedule_id",
        "run_type",
        "scheduled_for",
        "status",
        "owner_id",
    ):
        op.create_index(
            op.f(f"ix_job_search_runs_{column}"),
            "job_search_runs",
            [column],
            unique=False,
        )
    op.create_index(
        "uq_job_search_runs_automatic_schedule_time",
        "job_search_runs",
        ["schedule_id", "scheduled_for"],
        unique=True,
        sqlite_where=sa.text("run_type = 'automatic'"),
        postgresql_where=sa.text("run_type = 'automatic'"),
    )


def downgrade() -> None:
    op.drop_table("job_search_runs")
    op.drop_table("job_search_schedules")
    op.drop_table("job_search_configs")
