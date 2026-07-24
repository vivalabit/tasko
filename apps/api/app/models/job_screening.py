from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnerScoped


def utc_now() -> datetime:
    return datetime.now(UTC)


class JobScreeningDecisionRecord(OwnerScoped, Base):
    __tablename__ = "job_screening_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('keep', 'reject', 'uncertain')",
            name="ck_job_screening_decisions_decision",
        ),
        Index(
            "ix_job_screening_decisions_cache",
            "owner_id",
            "vacancy_hash",
            "config_hash",
            "model",
            "prompt_version",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid4().hex,
    )
    vacancy_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    config_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
    )
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    matched_rule_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    model: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    prompt_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    company: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )
