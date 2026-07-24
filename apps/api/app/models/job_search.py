from datetime import UTC, datetime, time
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
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
ScreeningField = Literal[
    "title",
    "company",
    "location",
    "description",
    "employment_type",
    "employmentType",
    "seniority",
    "salary_min",
    "salaryMin",
    "salary_max",
    "salaryMax",
    "posted_at",
    "postedAt",
    "source",
]
ScreeningOperator = Literal[
    "equals",
    "not_equals",
    "notEquals",
    "contains",
    "not_contains",
    "notContains",
    "starts_with",
    "startsWith",
    "ends_with",
    "endsWith",
    "greater_than",
    "greaterThan",
    "greater_than_or_equal",
    "greaterThanOrEqual",
    "less_than",
    "lessThan",
    "less_than_or_equal",
    "lessThanOrEqual",
    "in",
    "not_in",
    "notIn",
    "matches",
]
ScreeningValue = str | int | float | bool | list[str]
ScreeningSeniority = Literal[
    "intern",
    "entry",
    "junior",
    "associate",
    "mid",
    "senior",
    "lead",
    "director",
    "executive",
]


class SearchFilters(BaseModel):
    keywords: str = Field(default="", max_length=200)
    location: str = Field(default="", max_length=160)
    remote: Literal["Any", "Remote only", "Hybrid", "On-site"] = "Any"
    experience_level: Literal[
        "Any",
        "Entry level",
        "Associate",
        "Mid-Senior level",
        "Director",
    ] = Field(default="Any", alias="experienceLevel")
    job_type: Literal[
        "Any",
        "Full-time",
        "Part-time",
        "Contract",
        "Internship",
    ] = Field(default="Any", alias="jobType")
    date_posted: Literal[
        "Any time",
        "Past 24 hours",
        "Past week",
        "Past month",
    ] = Field(default="Any time", alias="datePosted")
    results_limit: int = Field(default=100, ge=1, le=1000, alias="resultsLimit")
    country: str = Field(default="Any", max_length=80)
    deduplicate: bool = True
    search_name: str = Field(default="", max_length=160, alias="searchName")
    folder: str = Field(default="", max_length=120)
    sources: list[JobSearchSource] | None = Field(default=None, max_length=10)
    parsers: list[JobSearchSource] | None = Field(default=None, max_length=10)

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }


class ScreeningRule(BaseModel):
    field: ScreeningField
    operator: ScreeningOperator
    value: ScreeningValue
    enabled: bool = True

    model_config = {
        "extra": "forbid",
        "strict": True,
    }


class ScreeningConfig(BaseModel):
    enabled: bool = False
    target_roles: list[str] = Field(
        default_factory=list,
        max_length=50,
        alias="targetRoles",
    )
    allowed_seniority: list[ScreeningSeniority] = Field(
        default_factory=list,
        max_length=9,
        alias="allowedSeniority",
    )
    excluded_seniority: list[ScreeningSeniority] = Field(
        default_factory=list,
        max_length=9,
        alias="excludedSeniority",
    )
    hard_rules: list[ScreeningRule] = Field(
        default_factory=list,
        max_length=100,
        alias="hardRules",
    )

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
        "strict": True,
    }

    @field_validator("target_roles")
    @classmethod
    def normalize_target_roles(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(role.strip() for role in value))
        if any(not role for role in normalized):
            raise ValueError("targetRoles must not contain empty roles")
        if any(len(role) > 160 for role in normalized):
            raise ValueError("targetRoles entries must be at most 160 characters")
        return normalized

    @field_validator("allowed_seniority", "excluded_seniority")
    @classmethod
    def deduplicate_seniority(
        cls,
        value: list[ScreeningSeniority],
    ) -> list[ScreeningSeniority]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def reject_conflicting_seniority(self) -> "ScreeningConfig":
        overlap = set(self.allowed_seniority).intersection(self.excluded_seniority)
        if overlap:
            conflicting = ", ".join(sorted(overlap))
            raise ValueError(
                "allowedSeniority and excludedSeniority must not overlap: "
                f"{conflicting}"
            )
        return self


class JobSearchConfigV2(BaseModel):
    schema_version: Literal[2] = Field(alias="schemaVersion")
    search: SearchFilters
    screening: ScreeningConfig = Field(default_factory=ScreeningConfig)

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
        "strict": True,
    }


LEGACY_SEARCH_ALIASES = {
    "query": "keywords",
    "experienceLevel": "experience_level",
    "jobType": "job_type",
    "datePosted": "date_posted",
    "resultsLimit": "results_limit",
    "searchName": "search_name",
}
VERSIONED_CONFIG_FIELDS = {"schemaVersion", "schema_version", "search", "screening"}


def normalize_job_search_config(config: dict[str, Any]) -> JobSearchConfigV2:
    if VERSIONED_CONFIG_FIELDS.intersection(config):
        return JobSearchConfigV2.model_validate(config)

    search_field_names = set(SearchFilters.model_fields)
    normalized_search = {
        normalized_key: value
        for key, value in config.items()
        if (normalized_key := LEGACY_SEARCH_ALIASES.get(key, key)) in search_field_names
    }
    return JobSearchConfigV2(
        schema_version=2,
        search=SearchFilters.model_validate(normalized_search),
    )


def validate_versioned_job_search_config(config: dict[str, Any]) -> dict[str, Any]:
    if not VERSIONED_CONFIG_FIELDS.intersection(config):
        return config
    return normalize_job_search_config(config).model_dump(
        by_alias=True,
        exclude_none=True,
    )


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

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_versioned_job_search_config(value)


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

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return validate_versioned_job_search_config(value)


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


class JobSearchManualRunRequest(BaseModel):
    config_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=36,
        alias="configId",
    )
    config: JobSearchConfigCreateRequest | None = None
    sources: list[JobSearchSource] = Field(min_length=1, max_length=10)
    ai_analysis_enabled: bool = Field(default=True, alias="aiAnalysisEnabled")

    model_config = {"extra": "forbid", "populate_by_name": True}

    @field_validator("sources")
    @classmethod
    def normalize_sources(
        cls,
        value: list[JobSearchSource],
    ) -> list[JobSearchSource]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def require_one_config_source(self) -> "JobSearchManualRunRequest":
        if bool(self.config_id) == bool(self.config):
            raise ValueError("provide exactly one of configId or config")
        return self


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


class JobSearchRunPayload(BaseModel):
    id: str
    schedule_id: str | None = Field(alias="scheduleId")
    run_type: Literal["manual", "automatic"] = Field(alias="runType")
    scheduled_for: datetime | None = Field(alias="scheduledFor")
    config_snapshot: dict[str, Any] = Field(alias="configSnapshot")
    sources: list[JobSearchSource]
    status: str
    jobs_found: int = Field(alias="jobsFound")
    jobs_added: int = Field(alias="jobsAdded")
    source_errors: dict[str, str] = Field(alias="sourceErrors")
    started_at: datetime = Field(alias="startedAt")
    completed_at: datetime | None = Field(alias="completedAt")
    warning: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}

    @field_validator(
        "scheduled_for",
        "started_at",
        "completed_at",
        mode="before",
    )
    @classmethod
    def normalize_timestamps(cls, value: datetime | None) -> datetime | None:
        return as_utc(value) if value is not None else None


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
