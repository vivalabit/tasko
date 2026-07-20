import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.documents import (
    DocumentGenerationArtifactRecord,
    DocumentPackJobRecord,
    DocumentValidationArtifactRecord,
    utc_now,
)
from app.services.ai_privacy import cleanup_expired_ai_data

logger = logging.getLogger(__name__)


def cleanup_expired_document_storage(
    session_factory: Callable[[], Session] = SessionLocal,
    *,
    now: datetime | None = None,
) -> tuple[int, int]:
    cutoff = now or utc_now()
    with session_factory() as db:
        artifact_result = db.execute(
            delete(DocumentValidationArtifactRecord).where(
                DocumentValidationArtifactRecord.expires_at <= cutoff
            )
        )
        generation_artifact_result = db.execute(
            delete(DocumentGenerationArtifactRecord).where(
                DocumentGenerationArtifactRecord.expires_at <= cutoff
            )
        )
        job_result = db.execute(
            delete(DocumentPackJobRecord).where(
                DocumentPackJobRecord.expires_at <= cutoff
            )
        )
        db.commit()
        deleted_artifacts = (artifact_result.rowcount or 0) + (
            generation_artifact_result.rowcount or 0
        )
        return deleted_artifacts, job_result.rowcount or 0


async def run_expiration_cleanup(interval_seconds: int) -> None:
    while True:
        try:
            deleted_artifacts, deleted_jobs, expired_owners, deleted_ai_records = (
                await asyncio.to_thread(cleanup_expired_storage)
            )
            if deleted_artifacts or deleted_jobs or expired_owners:
                logger.info(
                    "Expired storage cleaned up: artifacts=%d jobs=%d ai_owners=%d "
                    "ai_records=%d",
                    deleted_artifacts,
                    deleted_jobs,
                    expired_owners,
                    deleted_ai_records,
                )
        except Exception:
            logger.exception("Scheduled storage cleanup failed")
        await asyncio.sleep(interval_seconds)


def cleanup_expired_storage() -> tuple[int, int, int, int]:
    deleted_artifacts, deleted_jobs = cleanup_expired_document_storage()
    with SessionLocal() as db:
        expired_owners, deleted_ai_records = cleanup_expired_ai_data(db)
    return deleted_artifacts, deleted_jobs, expired_owners, deleted_ai_records
