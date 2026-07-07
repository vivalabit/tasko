from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.core.settings import Settings, get_settings
from app.models.jobs import StoredJobPayload, StoredJobRecord, StoredJobsRequest
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.ai_match import calculate_ai_matches

router = APIRouter()


@router.get("", response_model=list[StoredJobPayload])
def list_jobs(db: Session = Depends(get_db)) -> list[StoredJobPayload]:
    try:
        records = db.query(StoredJobRecord).order_by(StoredJobRecord.id.desc()).all()
        return [StoredJobPayload(id=record.id, data=record.data) for record in records]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc


@router.put("", response_model=list[StoredJobPayload])
def upsert_jobs(request: StoredJobsRequest, db: Session = Depends(get_db)) -> list[StoredJobPayload]:
    try:
        for job in request.jobs:
            record = db.get(StoredJobRecord, job.id)
            if record:
                record.data = job.data
            else:
                db.add(StoredJobRecord(id=job.id, data=job.data))

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
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[StoredJobPayload]:
    try:
        profile_record = db.get(ProfileRecord, "default")
        profile = (
            ProfilePayload.model_validate(profile_record.data)
            if profile_record
            else ProfilePayload()
        )
        matched_jobs = calculate_ai_matches(
            profile,
            [job.data for job in request.jobs],
            command=settings.openclaw_command,
            agent_id=settings.openclaw_agent_id,
            thinking=settings.openclaw_ai_match_thinking,
            timeout_seconds=settings.openclaw_ai_match_timeout_seconds,
            openclaw_enabled=settings.openclaw_ai_match_enabled,
            openclaw_max_jobs=settings.openclaw_ai_match_max_jobs,
        )

        for job in matched_jobs:
            job_id = str(job.get("id") or "")
            if not job_id:
                continue
            record = db.get(StoredJobRecord, job_id)
            if record:
                record.data = job
            else:
                db.add(StoredJobRecord(id=job_id, data=job))

        db.commit()
        return [StoredJobPayload(id=str(job.get("id")), data=job) for job in matched_jobs if job.get("id")]
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
        db.commit()
        return None
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Jobs database is unavailable",
        ) from exc
