from datetime import UTC, datetime, time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, OwnerScoped


def utc_now() -> datetime:
    return datetime.now(UTC)


class JobSearchConfigRecord(OwnerScoped, Base):
    __tablename__ = "job_search_configs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid4().hex,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )
    schedules: Mapped[list["JobSearchScheduleRecord"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
    )


class JobSearchScheduleRecord(OwnerScoped, Base):
    __tablename__ = "job_search_schedules"
    __table_args__ = (
        Index(
            "ix_job_search_schedules_due",
            "enabled",
            "next_run_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid4().hex,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    config_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("job_search_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    weekdays: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    local_time: Mapped[time] = mapped_column(Time(), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_analysis_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    config: Mapped[JobSearchConfigRecord] = relationship(back_populates="schedules")
    runs: Mapped[list["JobSearchRunRecord"]] = relationship(
        back_populates="schedule",
        passive_deletes=True,
    )


class JobSearchRunRecord(OwnerScoped, Base):
    __tablename__ = "job_search_runs"
    __table_args__ = (
        CheckConstraint(
            "run_type IN ('manual', 'automatic')",
            name="ck_job_search_runs_run_type",
        ),
        Index(
            "uq_job_search_runs_automatic_schedule_time",
            "schedule_id",
            "scheduled_for",
            unique=True,
            sqlite_where=text("run_type = 'automatic'"),
            postgresql_where=text("run_type = 'automatic'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: uuid4().hex,
    )
    schedule_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("job_search_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    run_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    jobs_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    jobs_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_errors: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    schedule: Mapped[JobSearchScheduleRecord | None] = relationship(
        back_populates="runs",
    )


JobSearchFrequency = Literal["daily", "weekdays", "selected_days"]
JobSearchSource = Literal["linkedin", "indeed", "jobs_ch"]


class JobSearchConfigCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    filters: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


class JobSearchConfigUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    filters: dict[str, Any] | None = None

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


class JobSearchConfigPayload(BaseModel):
    id: str
    name: str
    filters: dict[str, Any]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def normalize_timestamps(cls, value: datetime) -> datetime:
        return as_utc(value)


class JobSearchScheduleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    config_id: str = Field(min_length=1, max_length=36, alias="configId")
    sources: list[JobSearchSource] = Field(min_length=1, max_length=10)
    frequency: JobSearchFrequency
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    local_time: time = Field(alias="localTime")
    timezone: str = Field(min_length=1, max_length=64)
    ai_analysis_enabled: bool = Field(default=False, alias="aiAnalysisEnabled")
    enabled: bool = True

    model_config = {"extra": "forbid", "populate_by_name": True}

    @field_validator("name", "timezone")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("sources")
    @classmethod
    def normalize_sources(
        cls,
        value: list[JobSearchSource],
    ) -> list[JobSearchSource]:
        return list(dict.fromkeys(value))


class JobSearchScheduleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    config_id: str | None = Field(default=None, min_length=1, max_length=36, alias="configId")
    sources: list[JobSearchSource] | None = Field(default=None, min_length=1, max_length=10)
    frequency: JobSearchFrequency | None = None
    weekdays: list[int] | None = Field(default=None, max_length=7)
    local_time: time | None = Field(default=None, alias="localTime")
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    ai_analysis_enabled: bool | None = Field(default=None, alias="aiAnalysisEnabled")
    enabled: bool | None = None

    model_config = {"extra": "forbid", "populate_by_name": True}

    @field_validator("name", "timezone")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("sources")
    @classmethod
    def normalize_sources(
        cls,
        value: list[JobSearchSource] | None,
    ) -> list[JobSearchSource] | None:
        return list(dict.fromkeys(value)) if value is not None else None


class JobSearchSchedulePayload(BaseModel):
    id: str
    name: str
    config_id: str = Field(alias="configId")
    sources: list[JobSearchSource]
    frequency: JobSearchFrequency
    weekdays: list[int]
    local_time: time = Field(alias="localTime")
    timezone: str
    ai_analysis_enabled: bool = Field(alias="aiAnalysisEnabled")
    enabled: bool
    next_run_at: datetime | None = Field(alias="nextRunAt")
    last_run_at: datetime | None = Field(alias="lastRunAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"from_attributes": True, "populate_by_name": True}

    @field_validator(
        "next_run_at",
        "last_run_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value is not None else None


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
