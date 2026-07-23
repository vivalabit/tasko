from datetime import UTC, datetime, time
from typing import Any
from uuid import uuid4

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
