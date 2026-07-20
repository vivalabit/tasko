"""persist immutable document generation artifacts

Revision ID: 20260720_0009
Revises: 20260720_0008
Create Date: 2026-07-20 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260720_0009"
down_revision: str | None = "20260720_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_generation_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("application_id", sa.String(length=160), nullable=False),
        sa.Column("job_id", sa.String(length=160), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("template_content", sa.LargeBinary(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("generation_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("input_versions", sa.JSON(), nullable=False),
        sa.Column("validation_evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("result_content", sa.Text(), nullable=True),
        sa.Column("generation_model", sa.String(length=160), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["stored_applications.id"],
            name="fk_generation_artifacts_application",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["document_templates.id"],
            name="fk_generation_artifacts_template",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "application_id",
        "job_id",
        "template_id",
        "generation_fingerprint",
        "expires_at",
        "owner_id",
    ):
        op.create_index(
            op.f(f"ix_document_generation_artifacts_{column}"),
            "document_generation_artifacts",
            [column],
            unique=False,
        )

    op.add_column(
        "document_validation_artifacts",
        sa.Column("generation_artifact_id", sa.String(length=36), nullable=True),
    )
    with op.batch_alter_table("document_validation_artifacts") as batch_op:
        batch_op.create_foreign_key(
            "fk_validation_artifacts_generation_artifact",
            "document_generation_artifacts",
            ["generation_artifact_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            op.f("ix_document_validation_artifacts_generation_artifact_id"),
            ["generation_artifact_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("document_validation_artifacts") as batch_op:
        batch_op.drop_index(
            op.f("ix_document_validation_artifacts_generation_artifact_id")
        )
        batch_op.drop_constraint(
            "fk_validation_artifacts_generation_artifact",
            type_="foreignkey",
        )
        batch_op.drop_column("generation_artifact_id")
    op.drop_table("document_generation_artifacts")
