from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field
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
    job_id: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
        default="",
        server_default="",
        index=True,
    )
    search_config_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
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
    vacancy_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    manually_allowed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )


class JobScreeningAuditPayload(BaseModel):
    id: str
    job_id: str = Field(alias="jobId")
    decision: str
    reason_code: str = Field(alias="reasonCode")
    reason: str
    matched_rule_ids: list[str] = Field(alias="matchedRuleIds")
    config_hash: str = Field(alias="configHash")
    config_id: str | None = Field(default=None, alias="configId")
    model: str
    prompt_version: str = Field(alias="promptVersion")
    title: str
    company: str
    source_url: str = Field(alias="sourceUrl")
    checked_at: datetime = Field(alias="checkedAt")
    invalidated_at: datetime | None = Field(
        default=None,
        alias="invalidatedAt",
    )
    manually_allowed_at: datetime | None = Field(
        default=None,
        alias="manuallyAllowedAt",
    )
    can_recheck: bool = Field(alias="canRecheck")
    can_allow_manually: bool = Field(alias="canAllowManually")

    model_config = {"populate_by_name": True}
