import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.documents import (
    DocumentPackJobRecord,
    DocumentValidationArtifactRecord,
    utc_now,
)

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
        job_result = db.execute(
            delete(DocumentPackJobRecord).where(
                DocumentPackJobRecord.expires_at <= cutoff
            )
        )
        db.commit()
        return artifact_result.rowcount or 0, job_result.rowcount or 0


async def run_expiration_cleanup(interval_seconds: int) -> None:
    while True:
        try:
            deleted_artifacts, deleted_jobs = await asyncio.to_thread(
                cleanup_expired_document_storage
            )
            if deleted_artifacts or deleted_jobs:
                logger.info(
                    "Expired document storage cleaned up: artifacts=%d jobs=%d",
                    deleted_artifacts,
                    deleted_jobs,
                )
        except Exception:
            logger.exception("Scheduled document storage cleanup failed")
        await asyncio.sleep(interval_seconds)
