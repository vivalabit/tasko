from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.identity import get_bound_owner_id
from app.core.settings import Settings
from app.models.job_search import (
    JobSearchConfigRecord,
    JobSearchRunRecord,
    JobSearchScheduleRecord,
)
from app.models.jobs import StoredJobRecord
from app.models.parsers import LinkedInSearchRequest, ParsedJob
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.ai_match import AiMatchError, create_vacancy_matching_ai_facade
from app.services.ai_privacy import (
    has_current_ai_consent,
    privacy_settings_record,
)
from app.services.candidate_snapshot import (
    CandidateSnapshotError,
    get_candidate_match_snapshot,
)
from app.services.job_match_store import persist_job_and_match
from app.services.job_search_schedule import calculate_next_run_at
from app.services.vacancy_search import (
    VacancySearchRunResult,
    VacancySearchRunner,
    canonical_job_url,
    job_identity,
    normalize_identity_part,
)

AI_CONSENT_WARNING = "AI Match was skipped because current AI data-processing consent is missing"


class JobSearchExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class JobSearchExecutionResult:
    run: JobSearchRunRecord
    warning: str | None = None


def execute_job_search(
    db: Session,
    *,
    schedule: JobSearchScheduleRecord,
    config: JobSearchConfigRecord,
    runner: VacancySearchRunner,
    settings: Settings,
    run_type: str,
    scheduled_for: datetime | None = None,
    now: datetime | None = None,
) -> JobSearchExecutionResult:
    started_at = now or datetime.now(UTC)
    config_snapshot = build_config_snapshot(config)
    sources = list(schedule.sources)
    run = JobSearchRunRecord(
        id=uuid4().hex,
        schedule_id=schedule.id,
        run_type=run_type,
        scheduled_for=scheduled_for,
        config_snapshot=config_snapshot,
        sources=sources,
        status="running",
        jobs_found=0,
        jobs_added=0,
        source_errors={},
        started_at=started_at,
    )
    db.add(run)
    db.commit()

    try:
        request = search_request_from_config(config.filters)
        search_result = runner.run(
            sources=sources,
            request=request,
            wait_for_snapshots=True,
        )
    except (ValidationError, ValueError) as exc:
        run.status = "failed"
        run.source_errors = {"config": str(exc)[:500]}
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise JobSearchExecutionError("Stored job search config is invalid") from exc
    except Exception as exc:
        run.status = "failed"
        run.source_errors = {"runner": str(exc)[:500]}
        run.completed_at = datetime.now(UTC)
        db.commit()
        raise

    completed_at = datetime.now(UTC)
    new_jobs = persist_new_jobs(
        db,
        jobs=search_result.jobs,
        added_at=completed_at,
    )
    run.jobs_found = len(search_result.jobs)
    run.jobs_added = len(new_jobs)
    run.source_errors = search_result.source_errors
    run.status = run_status(search_result)
    run.completed_at = completed_at
    schedule.last_run_at = completed_at
    if schedule.enabled:
        schedule.next_run_at = calculate_next_run_at(
            frequency=schedule.frequency,
            weekdays=schedule.weekdays,
            local_time=schedule.local_time,
            timezone=schedule.timezone,
            now=completed_at,
        )
    else:
        schedule.next_run_at = None
    schedule.updated_at = completed_at
    db.commit()

    warning = match_new_jobs_if_allowed(
        db,
        jobs=new_jobs,
        enabled=schedule.ai_analysis_enabled,
        settings=settings,
        owner_id=get_bound_owner_id(),
    )
    db.refresh(run)
    return JobSearchExecutionResult(run=run, warning=warning)


def search_request_from_config(filters: dict[str, Any]) -> LinkedInSearchRequest:
    aliases = {
        "query": "keywords",
        "experienceLevel": "experience_level",
        "jobType": "job_type",
        "datePosted": "date_posted",
        "resultsLimit": "results_limit",
        "searchName": "search_name",
    }
    normalized = {aliases.get(key, key): value for key, value in filters.items()}
    return LinkedInSearchRequest.model_validate(normalized)


def build_config_snapshot(config: JobSearchConfigRecord) -> dict[str, Any]:
    return {
        "id": config.id,
        "name": config.name,
        "filters": deepcopy(config.filters),
        "createdAt": serialize_datetime(config.created_at),
        "updatedAt": serialize_datetime(config.updated_at),
    }


def persist_new_jobs(
    db: Session,
    *,
    jobs: list[ParsedJob],
    added_at: datetime,
) -> list[dict[str, Any]]:
    records = db.scalars(select(StoredJobRecord)).all()
    existing_ids = {record.id for record in records}
    existing_urls = {
        canonical_job_url(stored_job_url(record.data))
        for record in records
        if canonical_job_url(stored_job_url(record.data))
    }
    existing_identities = {
        stored_job_identity(record.data) for record in records if stored_job_identity(record.data)
    }
    added: list[dict[str, Any]] = []

    for index, job in enumerate(jobs):
        job_id = parsed_job_id(job, index=index)
        url_key = canonical_job_url(job.url)
        identity_key = job_identity(job)
        if (
            job_id in existing_ids
            or (url_key and url_key in existing_urls)
            or (identity_key and identity_key in existing_identities)
        ):
            continue
        data = parsed_job_to_stored_job(
            job,
            job_id=job_id,
            added_at=added_at,
        )
        db.add(StoredJobRecord(id=job_id, data=data, status="active"))
        existing_ids.add(job_id)
        if url_key:
            existing_urls.add(url_key)
        if identity_key:
            existing_identities.add(identity_key)
        added.append(data)
    return added


def match_new_jobs_if_allowed(
    db: Session,
    *,
    jobs: list[dict[str, Any]],
    enabled: bool,
    settings: Settings,
    owner_id: str,
) -> str | None:
    if not enabled or not jobs:
        return None
    consent = privacy_settings_record(db, owner_id)
    if not has_current_ai_consent(consent, settings):
        return AI_CONSENT_WARNING

    try:
        profile_record = db.get(ProfileRecord, "default")
        profile = (
            ProfilePayload.model_validate(profile_record.data)
            if profile_record
            else ProfilePayload()
        )
        candidate_snapshot = get_candidate_match_snapshot(
            db,
            profile=profile,
            settings=settings,
            allow_ai=True,
            strict_ai=True,
        )
        matched_jobs = create_vacancy_matching_ai_facade(settings).match(
            profile,
            jobs,
            candidate_snapshot=candidate_snapshot.data,
        )
        for matched_job in matched_jobs:
            persist_job_and_match(
                db,
                job=matched_job,
                profile_hash=candidate_snapshot.profile_hash,
            )
        assert consent is not None
        activity_at = datetime.now(UTC)
        consent.last_ai_activity_at = activity_at
        consent.ai_data_expires_at = activity_at + timedelta(days=consent.retention_days)
        consent.updated_at = activity_at
        db.commit()
        return None
    except (AiMatchError, CandidateSnapshotError, ValidationError) as exc:
        db.rollback()
        return f"AI Match failed for new vacancies: {str(exc)[:240]}"


def parsed_job_id(job: ParsedJob, *, index: int) -> str:
    source = normalize_source(job.source)
    identity = (
        job.url
        or f"{job.title or f'{source}-job'}-{job.company or 'company'}-"
        f"{job.location or 'location'}-{index}"
    )
    slug = re.sub(r"[^a-z0-9]+", "-", identity.casefold()).strip("-")[:96]
    return f"{source}-{slug or uuid4().hex}"


def parsed_job_to_stored_job(
    job: ParsedJob,
    *,
    job_id: str,
    added_at: datetime,
) -> dict[str, Any]:
    source = normalize_source(job.source)
    source_label = {
        "linkedin": "LinkedIn",
        "indeed": "Indeed",
        "jobs_ch": "jobs.ch",
    }[source]
    company = normalized_text(job.company, source_label)
    title = normalized_text(job.title, f"{source_label} vacancy")
    location = normalized_text(job.location, "Not specified")
    employment_type = normalized_text(job.employment_type, "Not specified")
    experience = normalized_text(job.seniority, "Not specified")
    overview = normalized_text(
        job.description,
        (
            f"Imported from {source_label}. Open the source vacancy to review "
            "the full description and apply details."
        ),
    )
    salary = normalized_text(job.salary, format_salary(job))
    source_url = normalized_text(job.url, "")
    apply_url = normalized_text(job.apply_url, source_url)
    return {
        "id": job_id,
        "company": company,
        "title": title,
        "location": location,
        "type": employment_type,
        "salary": salary,
        "posted": normalized_text(job.posted_at, source_label),
        "experience": experience,
        "department": f"{source_label} import",
        "match": 50,
        "logo": source,
        "overview": overview,
        "responsibilities": [
            f"Review the {source_label} vacancy details",
            "Compare requirements with your profile",
            "Decide whether to save or apply",
        ],
        "requirements": [
            item for item in (experience, employment_type, location) if item != "Not specified"
        ],
        "skills": [source_label, "Imported"],
        "salaryAverage": format_salary_amount(
            average(job.salary_min, job.salary_max),
            job.salary_currency,
        ),
        "salaryMin": format_salary_amount(job.salary_min, job.salary_currency),
        "salaryMax": format_salary_amount(job.salary_max, job.salary_currency),
        "recommendations": [],
        "companyInfo": (
            f"{company} vacancy imported from {source_label}"
            f"{f': {source_url}' if source_url else '.'}"
        ),
        "reviews": ["This vacancy was imported automatically and has not been reviewed yet."],
        "similarJobs": [],
        "applyUrl": apply_url or None,
        "sourceUrl": source_url or None,
        "addedAt": serialize_datetime(added_at),
    }


def run_status(result: VacancySearchRunResult) -> str:
    if not result.source_errors:
        return "completed"
    successful_sources = set(result.source_results) - set(result.source_errors)
    if successful_sources:
        return "partial"
    return "failed"


def stored_job_url(data: dict[str, Any]) -> str:
    return str(data.get("sourceUrl") or data.get("applyUrl") or "")


def stored_job_identity(data: dict[str, Any]) -> str:
    title = normalize_identity_part(str(data.get("title") or ""))
    company = normalize_identity_part(str(data.get("company") or ""))
    location = normalize_identity_part(str(data.get("location") or ""))
    if not title or not company:
        return ""
    return "|".join((title, company, location))


def normalize_source(value: str) -> str:
    if value in {"jobs_ch", "jobs.ch"}:
        return "jobs_ch"
    if value == "indeed":
        return "indeed"
    return "linkedin"


def normalized_text(value: str | None, fallback: str) -> str:
    return value.strip() if value and value.strip() else fallback


def format_salary(job: ParsedJob) -> str:
    minimum = format_salary_amount(job.salary_min, job.salary_currency)
    maximum = format_salary_amount(job.salary_max, job.salary_currency)
    values = [value for value in (minimum, maximum) if value != "N/A"]
    values = list(dict.fromkeys(values))
    return " – ".join(values) if values else "Not specified"


def format_salary_amount(value: int | None, currency: str | None) -> str:
    if value is None:
        return "N/A"
    prefix = f"{currency.strip()} " if currency and currency.strip() else ""
    return f"{prefix}{value:,}".replace(",", "'")


def average(minimum: int | None, maximum: int | None) -> int | None:
    if minimum is not None and maximum is not None:
        return round((minimum + maximum) / 2)
    return minimum if minimum is not None else maximum


def serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.astimezone(UTC).isoformat()
