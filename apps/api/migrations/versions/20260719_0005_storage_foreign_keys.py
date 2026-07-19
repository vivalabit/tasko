"""add foreign keys for expiring document storage

Revision ID: 20260719_0005
Revises: 20260719_0004
Create Date: 2026-07-19 15:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_0005"
down_revision: str | None = "20260719_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM document_validation_artifacts "
            "WHERE application_id NOT IN (SELECT id FROM stored_applications) "
            "OR template_id NOT IN (SELECT id FROM document_templates)"
        )
    )
    connection.execute(
        sa.text(
            "DELETE FROM document_pack_jobs "
            "WHERE application_id NOT IN (SELECT id FROM stored_applications)"
        )
    )

    with op.batch_alter_table("document_pack_jobs") as batch_op:
        batch_op.create_foreign_key(
            "fk_document_pack_jobs_application_id_stored_applications",
            "stored_applications",
            ["application_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("document_validation_artifacts") as batch_op:
        batch_op.create_foreign_key(
            "fk_document_validation_artifacts_application_id_stored_applications",
            "stored_applications",
            ["application_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_document_validation_artifacts_template_id_document_templates",
            "document_templates",
            ["template_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            op.f("ix_document_validation_artifacts_template_id"),
            ["template_id"],
            unique=False,
        )
        batch_op.create_index(
            op.f("ix_document_validation_artifacts_expires_at"),
            ["expires_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("document_validation_artifacts") as batch_op:
        batch_op.drop_index(op.f("ix_document_validation_artifacts_expires_at"))
        batch_op.drop_index(op.f("ix_document_validation_artifacts_template_id"))
        batch_op.drop_constraint(
            "fk_document_validation_artifacts_template_id_document_templates",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_document_validation_artifacts_application_id_stored_applications",
            type_="foreignkey",
        )

    with op.batch_alter_table("document_pack_jobs") as batch_op:
        batch_op.drop_constraint(
            "fk_document_pack_jobs_application_id_stored_applications",
            type_="foreignkey",
        )
