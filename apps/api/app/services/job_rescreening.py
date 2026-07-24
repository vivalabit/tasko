from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.identity import get_bound_owner_id
from app.core.settings import Settings
from app.models.job_search import (
    JobSearchConfigRecord,
    JobSearchRescreenPayload,
    normalize_job_search_config,
)
from app.models.jobs import StoredJobRecord
from app.models.parsers import ParsedJob
from app.services.job_screening import JOB_SCREENING_PROMPT_VERSION
from app.services.job_screening_store import (
    build_screening_config_hash,
    build_screening_vacancy_hash,
    sha256_json,
)
from app.services.job_search_execution import (
    NewJobCandidate,
    compact_screening_job,
    screen_new_job_candidates,
)

ACTIVE_JOB_STATUS = "active"
DISMISSED_JOB_STATUS = "dismissed"
SCREENED_OUT_JOB_STATUS = "screened_out"
IMPORTED_JOB_SOURCES = ("linkedin", "indeed", "jobs_ch")


class JobRescreeningError(RuntimeError):
    pass


class JobRescreeningConfirmationRequired(JobRescreeningError):
    pass


class JobRescreeningPlanChanged(JobRescreeningError):
    pass


@dataclass(frozen=True)
class EligibleStoredJob:
    record: StoredJobRecord
    candidate: NewJobCandidate


def rescreen_stored_jobs(
    db: Session,
    *,
    config: JobSearchConfigRecord,
    settings: Settings,
    dry_run: bool,
    confirm: bool,
    confirmation_token: str | None,
) -> JobSearchRescreenPayload:
    try:
        normalized_config = normalize_job_search_config(config.filters)
    except ValidationError as exc:
        raise JobRescreeningError(
            "The selected search config is invalid"
        ) from exc
    if not normalized_config.screening.enabled:
        raise JobRescreeningError(
            "The selected search config does not have screening enabled"
        )

    eligible = eligible_stored_jobs(db)
    screening_result = screen_new_job_candidates(
        db,
        candidates=[item.candidate for item in eligible],
        screening_config=normalized_config.screening,
        settings=settings,
    )
    if len(screening_result.decisions) != len(eligible):
        raise JobRescreeningError(
            "Vacancy screening did not produce a complete rescreening plan"
        )

    config_hash = build_screening_config_hash(normalized_config.screening)
    decision_by_id = {
        decision.id: decision
        for decision in screening_result.decisions
    }
    jobs_to_hide = [
        item
        for item in eligible
        if item.record.status == ACTIVE_JOB_STATUS
        and decision_by_id[item.record.id].decision != "keep"
    ]
    jobs_to_restore = [
        item
        for item in eligible
        if item.record.status == SCREENED_OUT_JOB_STATUS
        and decision_by_id[item.record.id].decision == "keep"
    ]
    plan_token = build_confirmation_token(
        eligible,
        decision_by_id=decision_by_id,
        config_hash=config_hash,
        settings=settings,
    )

    if not dry_run:
        if not confirm or not confirmation_token:
            raise JobRescreeningConfirmationRequired(
                "Run a dry run and explicitly confirm its rescreening plan"
            )
        if confirmation_token != plan_token:
            raise JobRescreeningPlanChanged(
                "The rescreening plan changed; run a new dry run before confirming"
            )
        for item in eligible:
            decision = decision_by_id[item.record.id]
            item.record.status = (
                ACTIVE_JOB_STATUS
                if decision.decision == "keep"
                else SCREENED_OUT_JOB_STATUS
            )
            item.record.dismissed_at = None

    return JobSearchRescreenPayload(
        configId=config.id,
        configHash=config_hash,
        dryRun=dry_run,
        applied=not dry_run,
        eligibleJobs=len(eligible),
        jobsScreened=screening_result.jobs_screened,
        jobsPassed=screening_result.jobs_passed,
        jobsRejected=screening_result.jobs_rejected,
        jobsUncertain=screening_result.jobs_uncertain,
        screeningErrors=screening_result.screening_errors,
        jobsToHide=len(jobs_to_hide),
        jobsToRestore=len(jobs_to_restore),
        jobsHidden=len(jobs_to_hide) if not dry_run else 0,
        jobsRestored=len(jobs_to_restore) if not dry_run else 0,
        confirmationToken=plan_token,
        warning=screening_result.warning,
    )


def eligible_stored_jobs(db: Session) -> list[EligibleStoredJob]:
    records = list(
        db.scalars(
            select(StoredJobRecord)
            .where(
                StoredJobRecord.status.in_(
                    (ACTIVE_JOB_STATUS, SCREENED_OUT_JOB_STATUS)
                )
            )
            .order_by(StoredJobRecord.id)
        ).all()
    )
    return [
        EligibleStoredJob(
            record=record,
            candidate=stored_job_candidate(record),
        )
        for record in records
        if is_automatically_imported(record)
    ]


def is_automatically_imported(record: StoredJobRecord) -> bool:
    source = imported_source_from_id(record.id)
    logo = normalize_imported_source(record.data.get("logo"))
    return bool(source and logo == source)


def imported_source_from_id(job_id: str) -> str:
    for source in IMPORTED_JOB_SOURCES:
        if job_id.startswith(f"{source}-"):
            return source
    return ""


def normalize_imported_source(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().casefold()
    return "jobs_ch" if normalized == "jobs.ch" else normalized


def stored_job_candidate(record: StoredJobRecord) -> NewJobCandidate:
    data = record.data
    source = imported_source_from_id(record.id)
    job = ParsedJob(
        source=source,
        title=text_value(data.get("title")),
        company=text_value(data.get("company")),
        location=text_value(data.get("location")),
        url=text_value(data.get("sourceUrl")),
        apply_url=text_value(data.get("applyUrl")),
        posted_at=text_value(data.get("posted")),
        employment_type=text_value(data.get("type")),
        seniority=text_value(data.get("experience")),
        description=text_value(data.get("overview")),
    )
    return NewJobCandidate(
        job=job,
        job_id=record.id,
        compact_data={
            "title": job.title or "",
            "company": job.company or "",
            "location": job.location or "",
            "description": job.description or "",
            "employmentType": job.employment_type or "",
            "seniority": job.seniority or "",
            "source": source,
            "postedAt": job.posted_at or "",
            "salaryMin": compact_value(data.get("salaryMin")),
            "salaryMax": compact_value(data.get("salaryMax")),
            "salaryCurrency": text_value(data.get("salaryCurrency")) or "",
        },
    )


def build_confirmation_token(
    eligible: list[EligibleStoredJob],
    *,
    decision_by_id: dict[str, Any],
    config_hash: str,
    settings: Settings,
) -> str:
    return sha256_json(
        {
            "ownerId": get_bound_owner_id(),
            "configHash": config_hash,
            "model": settings.job_screening_model,
            "promptVersion": JOB_SCREENING_PROMPT_VERSION,
            "jobs": [
                {
                    "id": item.record.id,
                    "status": item.record.status,
                    "vacancyHash": build_screening_vacancy_hash(
                        compact_screening_job(item.candidate),
                        max_description_chars=(
                            settings.job_screening_max_description_chars
                        ),
                    ),
                    "decision": decision_by_id[item.record.id].decision,
                }
                for item in eligible
            ],
        }
    )


def text_value(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def compact_value(value: object) -> int | float | str | None:
    return value if isinstance(value, (int, float, str)) else None
