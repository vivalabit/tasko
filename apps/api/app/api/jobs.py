from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.core.settings import Settings, get_settings
from app.models.jobs import (
    AiMatchJobStatus,
    JobMatchFeedbackRequest,
    StoredJobPayload,
    StoredJobRecord,
    StoredJobsRequest,
)
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.ai_match import JOB_ADDED_AT_FIELDS, OpenClawAiMatchError, calculate_ai_matches
from app.services.ai_match_jobs import ai_match_jobs
from app.services.candidate_snapshot import CandidateSnapshotError, get_candidate_match_snapshot
from app.services.job_match_store import (
    calibrate_job_with_feedback,
    delete_job_matches,
    hydrate_job_data,
    persist_job_and_match,
    persist_match_feedback,
    strip_ai_match,
)

router = APIRouter()


@router.get("", response_model=list[StoredJobPayload])
def list_jobs(db: Session = Depends(get_db)) -> list[StoredJobPayload]:
    try:
        profile = get_current_profile(db)
        candidate_snapshot = get_candidate_match_snapshot(db, profile=profile)
        records = db.query(StoredJobRecord).order_by(StoredJobRecord.id.desc()).all()
        return [
            StoredJobPayload(
                id=record.id,
                data=hydrate_job_data(
                    db,
                    job_id=record.id,
                    job_data=record.data,
                    profile_hash=candidate_snapshot.profile_hash,
                ),
            )
            for record in records
        ]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc


@router.put("", response_model=list[StoredJobPayload])
def upsert_jobs(request: StoredJobsRequest, db: Session = Depends(get_db)) -> list[StoredJobPayload]:
    try:
        now = datetime.now(UTC).isoformat()
        for job in request.jobs:
            record = db.get(StoredJobRecord, job.id)
            job_data = prepare_job_data(job.data, record, now)
            if record:
                record.data = strip_ai_match(job_data)
            else:
                db.add(StoredJobRecord(id=job.id, data=strip_ai_match(job_data)))

        db.commit()
        return list_jobs(db)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc


@router.post("/ai-match", response_model=list[StoredJobPayload])
def match_jobs(
    request: StoredJobsRequest,
    force: bool = False,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[StoredJobPayload]:
    try:
        now = datetime.now(UTC).isoformat()
        jobs_to_match = [
            prepare_job_data(job.data, db.get(StoredJobRecord, job.id), now)
            for job in request.jobs
        ]
        profile = get_current_profile(db)
        candidate_snapshot = get_candidate_match_snapshot(
            db,
            profile=profile,
            settings=settings,
            allow_openclaw=True,
            strict_openclaw=True,
        )
        jobs_to_match = [
            hydrate_job_data(
                db,
                job_id=str(job.get("id") or ""),
                job_data=job,
                profile_hash=candidate_snapshot.profile_hash,
            )
            for job in jobs_to_match
        ]
        matched_jobs = calculate_ai_matches(
            profile,
            jobs_to_match,
            command=settings.openclaw_command,
            agent_id=settings.openclaw_agent_id,
            thinking=settings.openclaw_ai_match_thinking,
            timeout_seconds=settings.openclaw_ai_match_timeout_seconds,
            openclaw_enabled=settings.openclaw_ai_match_enabled,
            openclaw_max_jobs=settings.openclaw_ai_match_max_jobs,
            force=force,
            candidate_snapshot=candidate_snapshot.data,
        )

        calibrated_jobs: list[dict[str, Any]] = []
        for job in matched_jobs:
            job_id = str(job.get("id") or "")
            if not job_id:
                continue
            calibrated_job = calibrate_job_with_feedback(
                db,
                job=job,
                profile_hash=candidate_snapshot.profile_hash,
            )
            persist_job_and_match(db, job=calibrated_job, profile_hash=candidate_snapshot.profile_hash)
            calibrated_jobs.append(calibrated_job)

        db.commit()
        return [StoredJobPayload(id=str(job.get("id")), data=job) for job in calibrated_jobs if job.get("id")]
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc
    except OpenClawAiMatchError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except CandidateSnapshotError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.post("/ai-match/run", response_model=AiMatchJobStatus, status_code=status.HTTP_202_ACCEPTED)
def run_match_jobs(
    request: StoredJobsRequest,
    force: bool = False,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AiMatchJobStatus:
    try:
        now = datetime.now(UTC).isoformat()
        jobs_to_match = [
            prepare_job_data(job.data, db.get(StoredJobRecord, job.id), now)
            for job in request.jobs
        ]
        profile = get_current_profile(db)
        candidate_snapshot = get_candidate_match_snapshot(
            db,
            profile=profile,
            settings=settings,
            allow_openclaw=True,
            strict_openclaw=True,
        )
        jobs_to_match = [
            hydrate_job_data(
                db,
                job_id=str(job.get("id") or ""),
                job_data=job,
                profile_hash=candidate_snapshot.profile_hash,
            )
            for job in jobs_to_match
        ]
        db.commit()
        session_factory = sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False)
        started, current_status = ai_match_jobs.start(
            profile=profile,
            jobs=jobs_to_match,
            profile_hash=candidate_snapshot.profile_hash,
            candidate_snapshot=candidate_snapshot.data,
            settings=settings,
            session_factory=session_factory,
            force=force,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc
    except CandidateSnapshotError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI match job is already running",
        )

    return current_status


@router.get("/ai-match/status", response_model=AiMatchJobStatus)
def get_match_jobs_status() -> AiMatchJobStatus:
    return ai_match_jobs.status()


def get_current_profile(db: Session) -> ProfilePayload:
    profile_record = db.get(ProfileRecord, "default")
    return (
        ProfilePayload.model_validate(profile_record.data)
        if profile_record
        else ProfilePayload()
    )


def prepare_job_data(
    job_data: dict[str, Any],
    record: StoredJobRecord | None,
    now: str,
) -> dict[str, Any]:
    next_job_data = dict(job_data)
    if has_added_at(next_job_data):
        return next_job_data

    if record and isinstance(record.data, dict):
        added_at = first_added_at(record.data)
        if added_at:
            next_job_data["addedAt"] = added_at
            return next_job_data

        return next_job_data

    next_job_data["addedAt"] = now
    return next_job_data


def has_added_at(job_data: dict[str, Any]) -> bool:
    return bool(first_added_at(job_data))


def first_added_at(job_data: dict[str, Any]) -> str:
    for field in JOB_ADDED_AT_FIELDS:
        value = job_data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@router.post("/{job_id}/match-feedback", response_model=StoredJobPayload)
def save_match_feedback(
    job_id: str,
    request: JobMatchFeedbackRequest,
    db: Session = Depends(get_db),
) -> StoredJobPayload:
    try:
        record = db.get(StoredJobRecord, job_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job was not found",
            )

        profile = get_current_profile(db)
        candidate_snapshot = get_candidate_match_snapshot(db, profile=profile)
        persist_match_feedback(
            db,
            job_id=job_id,
            profile_hash=candidate_snapshot.profile_hash,
            feedback=request.feedback,
        )
        db.commit()
        return StoredJobPayload(
            id=record.id,
            data=hydrate_job_data(
                db,
                job_id=record.id,
                job_data=record.data,
                profile_hash=candidate_snapshot.profile_hash,
            ),
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> None:
    try:
        record = db.get(StoredJobRecord, job_id)
        if not record:
            return None

        db.delete(record)
        delete_job_matches(db, job_id=job_id)
        db.commit()
        return None
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc
