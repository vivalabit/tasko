"""harden template deduplication and pack retention

Revision ID: 20260718_0003
Revises: 20260718_0002
Create Date: 2026-07-18 14:00:00.000000
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
import hashlib

import sqlalchemy as sa
from alembic import op


revision: str = "20260718_0003"
down_revision: str | None = "20260718_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_templates",
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
    )
    connection = op.get_bind()
    templates = connection.execute(
        sa.text(
            "SELECT id, type, content FROM document_templates "
            "ORDER BY created_at ASC, id ASC"
        )
    ).mappings()
    canonical_by_hash: dict[tuple[str, str], str] = {}
    for template in templates:
        content_sha256 = hashlib.sha256(template["content"]).hexdigest()
        key = (template["type"], content_sha256)
        canonical_id = canonical_by_hash.get(key)
        if canonical_id is None:
            canonical_by_hash[key] = template["id"]
            connection.execute(
                sa.text(
                    "UPDATE document_templates SET content_sha256 = :content_sha256 "
                    "WHERE id = :template_id"
                ),
                {"content_sha256": content_sha256, "template_id": template["id"]},
            )
            continue
        connection.execute(
            sa.text(
                "UPDATE document_files SET template_id = :canonical_id "
                "WHERE template_id = :duplicate_id"
            ),
            {"canonical_id": canonical_id, "duplicate_id": template["id"]},
        )
        connection.execute(
            sa.text("DELETE FROM document_templates WHERE id = :duplicate_id"),
            {"duplicate_id": template["id"]},
        )

    with op.batch_alter_table("document_templates") as batch_op:
        batch_op.alter_column(
            "content_sha256",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_document_templates_type_content_sha256",
            ["type", "content_sha256"],
        )

    op.add_column(
        "document_pack_jobs",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    jobs = connection.execute(
        sa.text("SELECT id, updated_at FROM document_pack_jobs")
    ).mappings()
    for job in jobs:
        updated_at = job["updated_at"]
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        connection.execute(
            sa.text(
                "UPDATE document_pack_jobs SET expires_at = :expires_at WHERE id = :job_id"
            ),
            {"expires_at": updated_at + timedelta(days=7), "job_id": job["id"]},
        )
    with op.batch_alter_table("document_pack_jobs") as batch_op:
        batch_op.alter_column(
            "expires_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
        batch_op.create_index(
            op.f("ix_document_pack_jobs_expires_at"),
            ["expires_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("document_pack_jobs") as batch_op:
        batch_op.drop_index(op.f("ix_document_pack_jobs_expires_at"))
        batch_op.drop_column("expires_at")
    with op.batch_alter_table("document_templates") as batch_op:
        batch_op.drop_constraint(
            "uq_document_templates_type_content_sha256",
            type_="unique",
        )
        batch_op.drop_column("content_sha256")
