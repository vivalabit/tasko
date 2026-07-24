from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_db
from app.core.identity import bind_request_identity
from app.core.settings import Settings, get_settings
from app.models.job_search import (
    JobSearchConfigCreateRequest,
    JobSearchConfigPayload,
    JobSearchConfigRecord,
    JobSearchConfigUpdateRequest,
    JobSearchManualRunRequest,
    JobSearchRescreenPayload,
    JobSearchRescreenRequest,
    JobSearchRunPayload,
    JobSearchRunRecord,
    JobSearchScheduleCreateRequest,
    JobSearchSchedulePayload,
    JobSearchScheduleRecord,
    JobSearchScheduleUpdateRequest,
)
from app.services.job_rescreening import (
    JobRescreeningConfirmationRequired,
    JobRescreeningError,
    JobRescreeningPlanChanged,
    rescreen_stored_jobs,
)
from app.services.job_search_execution import (
    JobSearchExecutionError,
    execute_job_search,
)
from app.services.job_search_schedule import (
    JobSearchScheduleValidationError,
    calculate_next_run_at,
    validate_search_schedule,
)
from app.services.job_search_worker import (
    has_active_schedule_run,
    schedule_execution_lock,
)
from app.services.vacancy_search import create_vacancy_search_runner

router = APIRouter(dependencies=[Depends(bind_request_identity)])

SCHEDULE_FIELDS = {
    "frequency",
    "weekdays",
    "local_time",
    "timezone",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


@router.get("/configs", response_model=list[JobSearchConfigPayload])
def list_configs(db: Session = Depends(get_db)) -> list[JobSearchConfigRecord]:
    try:
        return list(
            db.scalars(
                select(JobSearchConfigRecord).order_by(
                    JobSearchConfigRecord.updated_at.desc(),
                    JobSearchConfigRecord.id.desc(),
                )
            ).all()
        )
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.post(
    "/configs",
    response_model=JobSearchConfigPayload,
    status_code=status.HTTP_201_CREATED,
)
def create_config(
    request: JobSearchConfigCreateRequest,
    db: Session = Depends(get_db),
) -> JobSearchConfigRecord:
    now = utc_now()
    record = JobSearchConfigRecord(
        name=request.name,
        filters=request.filters,
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.get("/configs/{config_id}", response_model=JobSearchConfigPayload)
def get_config(
    config_id: str,
    db: Session = Depends(get_db),
) -> JobSearchConfigRecord:
    try:
        return require_config(db, config_id)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.patch("/configs/{config_id}", response_model=JobSearchConfigPayload)
@router.put("/configs/{config_id}", response_model=JobSearchConfigPayload)
def update_config(
    config_id: str,
    request: JobSearchConfigUpdateRequest,
    db: Session = Depends(get_db),
) -> JobSearchConfigRecord:
    try:
        record = require_config(db, config_id)
        fields = request.model_fields_set
        if "name" in fields:
            record.name = require_patch_value(request.name, "name")
        if "filters" in fields:
            record.filters = require_patch_value(request.filters, "filters")
        record.updated_at = utc_now()
        db.commit()
        db.refresh(record)
        return record
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.post(
    "/configs/{config_id}/rescreen",
    response_model=JobSearchRescreenPayload,
)
def rescreen_config_jobs(
    config_id: str,
    request: JobSearchRescreenRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobSearchRescreenPayload:
    try:
        config = require_config(db, config_id)
        result = rescreen_stored_jobs(
            db,
            config=config,
            settings=settings,
            dry_run=request.dry_run,
            confirm=request.confirm,
            confirmation_token=request.confirmation_token,
        )
        db.commit()
        return result
    except (
        JobRescreeningConfirmationRequired,
        JobRescreeningPlanChanged,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except JobRescreeningError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(config_id: str, db: Session = Depends(get_db)) -> None:
    try:
        record = require_config(db, config_id)
        schedule_id = db.scalar(
            select(JobSearchScheduleRecord.id).where(JobSearchScheduleRecord.config_id == config_id)
        )
        if schedule_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Config is used by one or more schedules",
            )
        db.delete(record)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.get("/schedules", response_model=list[JobSearchSchedulePayload])
def list_schedules(db: Session = Depends(get_db)) -> list[JobSearchScheduleRecord]:
    try:
        return list(
            db.scalars(
                select(JobSearchScheduleRecord).order_by(
                    JobSearchScheduleRecord.updated_at.desc(),
                    JobSearchScheduleRecord.id.desc(),
                )
            ).all()
        )
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.post(
    "/schedules",
    response_model=JobSearchSchedulePayload,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    request: JobSearchScheduleCreateRequest,
    db: Session = Depends(get_db),
) -> JobSearchScheduleRecord:
    try:
        require_config(db, request.config_id)
        now = utc_now()
        next_run_at = calculate_schedule_next_run(
            frequency=request.frequency,
            weekdays=request.weekdays,
            local_time=request.local_time,
            timezone=request.timezone,
            enabled=request.enabled,
            now=now,
        )
        record = JobSearchScheduleRecord(
            name=request.name,
            config_id=request.config_id,
            sources=request.sources,
            frequency=request.frequency,
            weekdays=request.weekdays,
            local_time=request.local_time,
            timezone=request.timezone,
            ai_analysis_enabled=request.ai_analysis_enabled,
            enabled=request.enabled,
            next_run_at=next_run_at,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except JobSearchScheduleValidationError as exc:
        db.rollback()
        raise invalid_schedule(exc) from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.get("/schedules/{schedule_id}", response_model=JobSearchSchedulePayload)
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
) -> JobSearchScheduleRecord:
    try:
        return require_schedule(db, schedule_id)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.patch("/schedules/{schedule_id}", response_model=JobSearchSchedulePayload)
@router.put("/schedules/{schedule_id}", response_model=JobSearchSchedulePayload)
def update_schedule(
    schedule_id: str,
    request: JobSearchScheduleUpdateRequest,
    db: Session = Depends(get_db),
) -> JobSearchScheduleRecord:
    try:
        record = require_schedule(db, schedule_id)
        fields = request.model_fields_set
        if "config_id" in fields:
            config_id = require_patch_value(request.config_id, "configId")
            require_config(db, config_id)
            record.config_id = config_id
        if "name" in fields:
            record.name = require_patch_value(request.name, "name")
        if "sources" in fields:
            record.sources = require_patch_value(request.sources, "sources")
        if "frequency" in fields:
            record.frequency = require_patch_value(request.frequency, "frequency")
        if "weekdays" in fields:
            record.weekdays = require_patch_value(request.weekdays, "weekdays")
        if "local_time" in fields:
            record.local_time = require_patch_value(request.local_time, "localTime")
        if "timezone" in fields:
            record.timezone = require_patch_value(request.timezone, "timezone")
        if "ai_analysis_enabled" in fields:
            record.ai_analysis_enabled = require_patch_value(
                request.ai_analysis_enabled,
                "aiAnalysisEnabled",
            )
        if "enabled" in fields:
            record.enabled = require_patch_value(request.enabled, "enabled")

        validate_search_schedule(
            frequency=record.frequency,
            weekdays=record.weekdays,
            local_time=record.local_time,
            timezone=record.timezone,
        )
        if SCHEDULE_FIELDS.intersection(fields) or "enabled" in fields:
            record.next_run_at = calculate_schedule_next_run(
                frequency=record.frequency,
                weekdays=record.weekdays,
                local_time=record.local_time,
                timezone=record.timezone,
                enabled=record.enabled,
                now=utc_now(),
            )
        record.updated_at = utc_now()
        db.commit()
        db.refresh(record)
        return record
    except JobSearchScheduleValidationError as exc:
        db.rollback()
        raise invalid_schedule(exc) from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)) -> None:
    try:
        db.delete(require_schedule(db, schedule_id))
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.post(
    "/run",
    response_model=JobSearchRunPayload,
)
def run_manual_search(
    request: JobSearchManualRunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobSearchRunPayload:
    try:
        config = require_config(db, request.config_id) if request.config_id else None
        inline_config = request.config
        config_snapshot = (
            None
            if config is not None
            else {
                "id": None,
                "name": inline_config.name,
                "filters": inline_config.filters,
                "createdAt": None,
                "updatedAt": None,
            }
        )
        result = execute_job_search(
            db,
            schedule=None,
            config=config,
            config_snapshot=config_snapshot,
            sources=list(request.sources),
            ai_analysis_enabled=request.ai_analysis_enabled,
            runner=create_vacancy_search_runner(settings),
            settings=settings,
            run_type="manual",
            recalculate_schedule=False,
        )
        payload = JobSearchRunPayload.model_validate(result.run)
        return payload.model_copy(update={"warning": result.warning})
    except JobSearchExecutionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Vacancy search execution failed",
        ) from exc


@router.post(
    "/schedules/{schedule_id}/run",
    response_model=JobSearchRunPayload,
)
def run_schedule_now(
    schedule_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JobSearchRunPayload:
    try:
        schedule = require_schedule(db, schedule_id)
        config = require_config(db, schedule.config_id)
        with schedule_execution_lock(db, schedule.id) as acquired:
            if not acquired or has_active_schedule_run(db, schedule.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Job search schedule is already running",
                )
            result = execute_job_search(
                db,
                schedule=schedule,
                config=config,
                runner=create_vacancy_search_runner(settings),
                settings=settings,
                run_type="manual",
            )
        payload = JobSearchRunPayload.model_validate(result.run)
        return payload.model_copy(update={"warning": result.warning})
    except JobSearchExecutionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Vacancy search execution failed",
        ) from exc


@router.get("/runs", response_model=list[JobSearchRunPayload])
def list_runs(
    schedule_id: str | None = Query(default=None, alias="scheduleId"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[JobSearchRunRecord]:
    try:
        query = select(JobSearchRunRecord)
        if schedule_id is not None:
            query = query.where(JobSearchRunRecord.schedule_id == schedule_id)
        return list(
            db.scalars(
                query.order_by(
                    JobSearchRunRecord.started_at.desc(),
                    JobSearchRunRecord.id.desc(),
                ).limit(limit)
            ).all()
        )
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


def require_config(db: Session, config_id: str) -> JobSearchConfigRecord:
    record = db.get(JobSearchConfigRecord, config_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job search config not found",
        )
    return record


def require_schedule(db: Session, schedule_id: str) -> JobSearchScheduleRecord:
    record = db.get(JobSearchScheduleRecord, schedule_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job search schedule not found",
        )
    return record


def calculate_schedule_next_run(
    *,
    frequency: str,
    weekdays: list[int],
    local_time: time,
    timezone: str,
    enabled: bool,
    now: datetime,
) -> datetime | None:
    if not enabled:
        validate_search_schedule(
            frequency=frequency,
            weekdays=weekdays,
            local_time=local_time,
            timezone=timezone,
        )
        return None
    return calculate_next_run_at(
        frequency=frequency,
        weekdays=weekdays,
        local_time=local_time,
        timezone=timezone,
        now=now,
    )


def require_patch_value(value: Any, field_name: str) -> Any:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must not be null",
        )
    return value


def invalid_schedule(exc: JobSearchScheduleValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=str(exc),
    )


def database_unavailable(exc: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Job search database is unavailable",
    )
