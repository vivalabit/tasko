from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.identity import get_bound_owner_id
from app.models.job_screening import JobScreeningDecisionRecord
from app.models.job_search import ScreeningConfig
from app.services.job_screening import (
    CompactScreeningJob,
    JobScreeningDecision,
    validate_compact_jobs,
    validate_screening_config,
)


def build_screening_config_hash(
    screening_config: ScreeningConfig | dict[str, Any],
) -> str:
    config = validate_screening_config(screening_config)
    return sha256_json(
        config.model_dump(
            by_alias=True,
            exclude_none=True,
        )
    )


def build_screening_vacancy_hash(
    job: CompactScreeningJob | dict[str, Any],
    *,
    max_description_chars: int = 12_000,
) -> str:
    compact_job = validate_compact_jobs(
        [job],
        max_description_chars=max_description_chars,
    )[0]
    return sha256_json(
        compact_job.model_dump(
            by_alias=True,
            exclude_none=True,
        )
    )


def persist_screening_decision(
    db: Session,
    *,
    vacancy_hash: str,
    config_hash: str,
    decision: JobScreeningDecision | dict[str, Any],
    model: str,
    prompt_version: str,
    title: str | None,
    company: str | None,
    source_url: str | None,
    created_at: datetime | None = None,
) -> JobScreeningDecisionRecord:
    validated_decision = (
        decision
        if isinstance(decision, JobScreeningDecision)
        else JobScreeningDecision.model_validate(decision)
    )
    require_sha256(vacancy_hash, field_name="vacancy_hash")
    require_sha256(config_hash, field_name="config_hash")
    normalized_model = require_text(model, field_name="model", max_length=160)
    normalized_prompt_version = require_text(
        prompt_version,
        field_name="prompt_version",
        max_length=64,
    )
    record = JobScreeningDecisionRecord(
        id=uuid4().hex,
        owner_id=get_bound_owner_id(),
        vacancy_hash=vacancy_hash,
        config_hash=config_hash,
        decision=validated_decision.decision,
        reason_code=validated_decision.reason_code,
        reason=validated_decision.reason,
        matched_rule_ids=list(validated_decision.matched_rule_ids),
        model=normalized_model,
        prompt_version=normalized_prompt_version,
        title=normalize_metadata(title, max_length=500),
        company=normalize_metadata(company, max_length=500),
        source_url=normalize_metadata(source_url, max_length=8_000),
        created_at=as_utc(created_at or datetime.now(UTC)),
    )
    db.add(record)
    return record


def latest_screening_decision(
    db: Session,
    *,
    vacancy_hash: str,
    config_hash: str,
    model: str,
    prompt_version: str,
) -> JobScreeningDecisionRecord | None:
    require_sha256(vacancy_hash, field_name="vacancy_hash")
    require_sha256(config_hash, field_name="config_hash")
    normalized_model = require_text(model, field_name="model", max_length=160)
    normalized_prompt_version = require_text(
        prompt_version,
        field_name="prompt_version",
        max_length=64,
    )
    return db.scalar(
        select(JobScreeningDecisionRecord)
        .where(
            JobScreeningDecisionRecord.owner_id == get_bound_owner_id(),
            JobScreeningDecisionRecord.vacancy_hash == vacancy_hash,
            JobScreeningDecisionRecord.config_hash == config_hash,
            JobScreeningDecisionRecord.model == normalized_model,
            JobScreeningDecisionRecord.prompt_version
            == normalized_prompt_version,
        )
        .order_by(
            JobScreeningDecisionRecord.created_at.desc(),
            JobScreeningDecisionRecord.id.desc(),
        )
        .limit(1)
    )


def sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_sha256(value: str, *, field_name: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef"
        for character in value
    ):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def require_text(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} must be at most {max_length} characters")
    return normalized


def normalize_metadata(
    value: str | None,
    *,
    max_length: int,
) -> str:
    return (value or "").strip()[:max_length]


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
