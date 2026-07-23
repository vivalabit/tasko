"""scope stored jobs and match feedback to authenticated owners

Revision ID: 20260723_0014
Revises: 20260722_0013
Create Date: 2026-07-23 11:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260723_0014"
down_revision: str | None = "20260722_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_OWNER_ID = "local-owner"


def upgrade() -> None:
    op.create_table(
        "stored_jobs_owner_scoped",
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("owner_id", "id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO stored_jobs_owner_scoped "
            "(owner_id, id, data, status, dismissed_at) "
            "SELECT :owner_id, id, data, status, dismissed_at FROM stored_jobs"
        ).bindparams(owner_id=LEGACY_OWNER_ID)
    )
    op.drop_table("stored_jobs")
    op.rename_table("stored_jobs_owner_scoped", "stored_jobs")
    op.create_index(
        op.f("ix_stored_jobs_owner_id"),
        "stored_jobs",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stored_jobs_status"),
        "stored_jobs",
        ["status"],
        unique=False,
    )

    op.add_column(
        "job_match_feedback",
        sa.Column(
            "owner_id",
            sa.String(length=160),
            nullable=False,
            server_default=LEGACY_OWNER_ID,
        ),
    )
    with op.batch_alter_table("job_match_feedback") as batch_op:
        batch_op.alter_column(
            "owner_id",
            existing_type=sa.String(length=160),
            nullable=False,
            server_default=None,
        )
        batch_op.create_index(
            op.f("ix_job_match_feedback_owner_id"),
            ["owner_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("job_match_feedback") as batch_op:
        batch_op.drop_index(op.f("ix_job_match_feedback_owner_id"))
        batch_op.drop_column("owner_id")

    connection = op.get_bind()
    rows = (
        connection.execute(
            sa.text(
                "SELECT owner_id, id FROM stored_jobs "
                "ORDER BY id ASC, "
                "CASE WHEN owner_id = :legacy_owner_id THEN 0 ELSE 1 END, "
                "owner_id ASC"
            ),
            {"legacy_owner_id": LEGACY_OWNER_ID},
        )
        .mappings()
        .all()
    )
    seen_job_ids: set[str] = set()
    for row in rows:
        job_id = row["id"]
        if job_id not in seen_job_ids:
            seen_job_ids.add(job_id)
            continue
        connection.execute(
            sa.text("DELETE FROM stored_jobs WHERE owner_id = :owner_id AND id = :job_id"),
            {"owner_id": row["owner_id"], "job_id": job_id},
        )

    op.create_table(
        "stored_jobs_unscoped",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO stored_jobs_unscoped (id, data, status, dismissed_at) "
            "SELECT id, data, status, dismissed_at FROM stored_jobs"
        )
    )
    op.drop_table("stored_jobs")
    op.rename_table("stored_jobs_unscoped", "stored_jobs")
    op.create_index(
        op.f("ix_stored_jobs_status"),
        "stored_jobs",
        ["status"],
        unique=False,
    )
