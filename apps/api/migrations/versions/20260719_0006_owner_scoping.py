"""scope application data to authenticated owners

Revision ID: 20260719_0006
Revises: 20260719_0005
Create Date: 2026-07-19 16:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_0006"
down_revision: str | None = "20260719_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_OWNER_ID = "local-owner"
OWNER_TABLES = (
    "stored_applications",
    "stored_application_events",
    "candidate_confirmations",
    "documents",
    "document_pack_jobs",
    "document_validation_artifacts",
    "document_templates",
    "workspace_source_documents",
)


def upgrade() -> None:
    for table_name in OWNER_TABLES:
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

    with op.batch_alter_table("document_templates") as batch_op:
        batch_op.drop_constraint(
            "uq_document_templates_type_content_sha256",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_document_templates_owner_type_content_sha256",
            ["owner_id", "type", "content_sha256"],
        )


def downgrade() -> None:
    connection = op.get_bind()
    templates = connection.execute(
        sa.text(
            "SELECT id, type, content_sha256 FROM document_templates "
            "ORDER BY created_at ASC, id ASC"
        )
    ).mappings()
    canonical_by_hash: dict[tuple[str, str], str] = {}
    for template in templates:
        key = (template["type"], template["content_sha256"])
        canonical_id = canonical_by_hash.get(key)
        if canonical_id is None:
            canonical_by_hash[key] = template["id"]
            continue
        connection.execute(
            sa.text(
                "UPDATE document_files SET template_id = :canonical_id "
                "WHERE template_id = :duplicate_id"
            ),
            {"canonical_id": canonical_id, "duplicate_id": template["id"]},
        )
        connection.execute(
            sa.text(
                "UPDATE document_validation_artifacts SET template_id = :canonical_id "
                "WHERE template_id = :duplicate_id"
            ),
            {"canonical_id": canonical_id, "duplicate_id": template["id"]},
        )
        connection.execute(
            sa.text("DELETE FROM document_templates WHERE id = :duplicate_id"),
            {"duplicate_id": template["id"]},
        )

    with op.batch_alter_table("document_templates") as batch_op:
        batch_op.drop_constraint(
            "uq_document_templates_owner_type_content_sha256",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_document_templates_type_content_sha256",
            ["type", "content_sha256"],
        )

    for table_name in reversed(OWNER_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(op.f(f"ix_{table_name}_owner_id"))
            batch_op.drop_column("owner_id")
