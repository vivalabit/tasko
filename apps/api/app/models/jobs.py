from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, OwnerScoped


class StoredJobRecord(Base):
    __tablename__ = "stored_jobs"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class JobMatchRecord(OwnerScoped, Base):
    __tablename__ = "job_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    profile_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    matcher_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    cache_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    gaps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    heuristic_score: Mapped[int] = mapped_column(Integer, nullable=False)
    openclaw_error: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class JobMatchFeedbackRecord(Base):
    __tablename__ = "job_match_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    profile_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    matcher_version: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    feedback: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class StoredJobPayload(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    data: dict[str, Any]


class StoredJobsRequest(BaseModel):
    jobs: list[StoredJobPayload] = Field(default_factory=list)


class JobMatchFeedbackRequest(BaseModel):
    feedback: Literal["good_match", "bad_match", "not_interested"]


class AiMatchJobStatus(BaseModel):
    run_id: str = Field(default="", alias="runId")
    status: Literal["idle", "queued", "running", "completed", "failed"] = "idle"
    total: int = 0
    processed: int = 0
    updated_jobs: list[StoredJobPayload] = Field(default_factory=list, alias="updatedJobs")
    error: str | None = None

    model_config = {"populate_by_name": True}
