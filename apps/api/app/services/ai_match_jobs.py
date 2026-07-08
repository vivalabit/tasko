from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models.jobs import AiMatchJobStatus, StoredJobPayload
from app.models.profile import ProfilePayload
from app.services.ai_match import calculate_ai_matches
from app.services.job_match_store import calibrate_job_with_feedback, hydrate_job_data, persist_job_and_match

SessionFactory = Callable[[], Session]


class AiMatchJobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status = AiMatchJobStatus()

    def start(
        self,
        *,
        profile: ProfilePayload,
        jobs: list[dict[str, Any]],
        profile_hash: str,
        candidate_snapshot: dict[str, Any],
        settings: Settings,
        session_factory: SessionFactory,
        force: bool = False,
    ) -> tuple[bool, AiMatchJobStatus]:
        with self._lock:
            if self._status.status in {"queued", "running"}:
                return False, self._status.model_copy(deep=True)

            run_id = uuid4().hex
            self._status = AiMatchJobStatus(
                runId=run_id,
                status="queued",
                total=len(jobs),
                processed=0,
                updatedJobs=[],
            )

        thread = threading.Thread(
            target=self._run,
            kwargs={
                "run_id": run_id,
                "profile": profile,
                "jobs": jobs,
                "profile_hash": profile_hash,
                "candidate_snapshot": candidate_snapshot,
                "settings": settings,
                "session_factory": session_factory,
                "force": force,
            },
            daemon=True,
        )
        thread.start()
        return True, self.status()

    def status(self) -> AiMatchJobStatus:
        with self._lock:
            return self._status.model_copy(deep=True)

    def _run(
        self,
        *,
        run_id: str,
        profile: ProfilePayload,
        jobs: list[dict[str, Any]],
        profile_hash: str,
        candidate_snapshot: dict[str, Any],
        settings: Settings,
        session_factory: SessionFactory,
        force: bool,
    ) -> None:
        self._update(run_id, status="running")

        try:
            for job in jobs:
                matched_job = calculate_ai_matches(
                    profile,
                    [job],
                    command=settings.openclaw_command,
                    agent_id=settings.openclaw_agent_id,
                    thinking=settings.openclaw_ai_match_thinking,
                    timeout_seconds=settings.openclaw_ai_match_timeout_seconds,
                    openclaw_enabled=settings.openclaw_ai_match_enabled,
                    openclaw_max_jobs=1,
                    force=force,
                    candidate_snapshot=candidate_snapshot,
                )
                if not matched_job:
                    self._increment(run_id)
                    continue

                openclaw_job = matched_job[0]
                hydrated_job = self._persist_job(session_factory, openclaw_job, profile_hash)
                self._append_update(run_id, hydrated_job)

            self._update(run_id, status="completed")
        except Exception as exc:
            self._update(run_id, status="failed", error=str(exc)[:240])

    def _persist_job(
        self,
        session_factory: SessionFactory,
        job: dict[str, Any],
        profile_hash: str,
    ) -> dict[str, Any]:
        job_id = str(job.get("id") or "")
        if not job_id:
            return job

        db = session_factory()
        try:
            calibrated_job = calibrate_job_with_feedback(db, job=job, profile_hash=profile_hash)
            persist_job_and_match(db, job=calibrated_job, profile_hash=profile_hash)
            db.commit()
            return hydrate_job_data(db, job_id=job_id, job_data=calibrated_job, profile_hash=profile_hash)
        except SQLAlchemyError:
            db.rollback()
            raise
        finally:
            db.close()

    def _append_update(self, run_id: str, job: dict[str, Any]) -> None:
        job_id = str(job.get("id") or "")
        if not job_id:
            self._increment(run_id)
            return

        payload = StoredJobPayload(id=job_id, data=job)
        with self._lock:
            if self._status.run_id != run_id:
                return

            updates = [item for item in self._status.updated_jobs if item.id != job_id]
            updates.append(payload)
            self._status.updated_jobs = updates
            self._status.processed = min(self._status.total, self._status.processed + 1)

    def _increment(self, run_id: str) -> None:
        with self._lock:
            if self._status.run_id != run_id:
                return
            self._status.processed = min(self._status.total, self._status.processed + 1)

    def _add_total(self, run_id: str, amount: int) -> None:
        with self._lock:
            if self._status.run_id != run_id:
                return
            self._status.total += amount

    def _update(self, run_id: str, **changes: Any) -> None:
        with self._lock:
            if self._status.run_id != run_id:
                return
            for key, value in changes.items():
                setattr(self._status, key, value)


ai_match_jobs = AiMatchJobManager()
