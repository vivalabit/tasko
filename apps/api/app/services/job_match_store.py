from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.jobs import JobMatchFeedbackRecord, JobMatchRecord, StoredJobRecord
from app.services.ai_match import MATCHER_VERSION

FEEDBACK_SCORE_ADJUSTMENTS = {
    "good_match": 8,
    "bad_match": -12,
    "not_interested": -25,
}
FEEDBACK_LABELS = {
    "good_match": "User marked this as a good match",
    "bad_match": "User marked this as a bad match",
    "not_interested": "User marked this as not interesting",
}


def hydrate_job_data(
    db: Session,
    *,
    job_id: str,
    job_data: dict[str, Any],
    profile_hash: str,
) -> dict[str, Any]:
    next_job_data = dict(job_data)
    match_record = latest_match_record(db, job_id=job_id, profile_hash=profile_hash)
    if match_record:
        next_job_data["match"] = match_record.score
        next_job_data["aiMatch"] = match_record_to_ai_match(match_record)
        feedback_record = latest_feedback_record(db, job_id=job_id, profile_hash=profile_hash)
        if feedback_record:
            next_job_data["aiMatch"]["feedback"] = feedback_record.feedback
        return next_job_data

    return next_job_data


def latest_match_record(db: Session, *, job_id: str, profile_hash: str) -> JobMatchRecord | None:
    return (
        db.query(JobMatchRecord)
        .filter(
            JobMatchRecord.job_id == job_id,
            JobMatchRecord.profile_hash == profile_hash,
            JobMatchRecord.matcher_version == MATCHER_VERSION,
            JobMatchRecord.source == "openclaw",
        )
        .order_by(JobMatchRecord.created_at.desc(), JobMatchRecord.id.desc())
        .first()
    )


def strip_ai_match(job_data: dict[str, Any]) -> dict[str, Any]:
    next_job_data = dict(job_data)
    next_job_data.pop("aiMatch", None)
    return next_job_data


def persist_job_and_match(db: Session, *, job: dict[str, Any], profile_hash: str) -> None:
    job_id = str(job.get("id") or "")
    if not job_id:
        return

    job_data = strip_ai_match(job)
    record = db.get(StoredJobRecord, job_id)
    if record:
        record.data = job_data
    else:
        db.add(StoredJobRecord(id=job_id, data=job_data))

    ai_match = job.get("aiMatch")
    if isinstance(ai_match, dict) and should_insert_match_record(db, job_id, profile_hash, ai_match):
        db.add(build_match_record(job_id=job_id, profile_hash=profile_hash, ai_match=ai_match))


def delete_job_matches(db: Session, *, job_id: str) -> None:
    db.query(JobMatchRecord).filter(JobMatchRecord.job_id == job_id).delete()
    db.query(JobMatchFeedbackRecord).filter(JobMatchFeedbackRecord.job_id == job_id).delete()


def persist_match_feedback(
    db: Session,
    *,
    job_id: str,
    profile_hash: str,
    feedback: str,
) -> JobMatchFeedbackRecord:
    record = JobMatchFeedbackRecord(
        id=uuid4().hex,
        job_id=job_id,
        profile_hash=profile_hash,
        matcher_version=MATCHER_VERSION,
        feedback=feedback,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    return record


def latest_feedback_record(
    db: Session,
    *,
    job_id: str,
    profile_hash: str,
) -> JobMatchFeedbackRecord | None:
    return (
        db.query(JobMatchFeedbackRecord)
        .filter(
            JobMatchFeedbackRecord.job_id == job_id,
            JobMatchFeedbackRecord.profile_hash == profile_hash,
            JobMatchFeedbackRecord.matcher_version == MATCHER_VERSION,
        )
        .order_by(JobMatchFeedbackRecord.created_at.desc(), JobMatchFeedbackRecord.id.desc())
        .first()
    )


def calibrate_job_with_feedback(
    db: Session,
    *,
    job: dict[str, Any],
    profile_hash: str,
) -> dict[str, Any]:
    job_id = str(job.get("id") or "")
    ai_match = job.get("aiMatch")
    if not job_id or not isinstance(ai_match, dict):
        return job

    feedback_record = latest_feedback_record(db, job_id=job_id, profile_hash=profile_hash)
    if not feedback_record:
        return job

    adjustment = FEEDBACK_SCORE_ADJUSTMENTS.get(feedback_record.feedback, 0)
    if adjustment == 0:
        return job

    next_job = dict(job)
    next_ai_match = dict(ai_match)
    calibrated_score = clamp_int(next_ai_match.get("score"), clamp_int(next_job.get("match"), 0))
    calibrated_score = max(0, min(100, calibrated_score + adjustment))
    next_job["match"] = calibrated_score
    next_ai_match["score"] = calibrated_score
    next_ai_match["feedback"] = feedback_record.feedback
    next_ai_match["calibration"] = {
        "feedback": feedback_record.feedback,
        "adjustment": adjustment,
    }

    label = FEEDBACK_LABELS.get(feedback_record.feedback, "User feedback adjusted this match")
    if adjustment > 0:
        reasons = normalize_string_list(next_ai_match.get("reasons"))
        if label not in reasons:
            reasons = [label, *reasons][:3]
        next_ai_match["reasons"] = reasons
    else:
        gaps = normalize_string_list(next_ai_match.get("gaps"))
        if label not in gaps:
            gaps = [label, *gaps][:3]
        next_ai_match["gaps"] = gaps

    next_job["aiMatch"] = next_ai_match
    return next_job


def should_insert_match_record(
    db: Session,
    job_id: str,
    profile_hash: str,
    ai_match: dict[str, Any],
) -> bool:
    latest = latest_match_record(db, job_id=job_id, profile_hash=profile_hash)
    if not latest:
        return True

    return match_record_to_ai_match(latest) != normalize_ai_match(ai_match, latest.created_at)


def build_match_record(job_id: str, profile_hash: str, ai_match: dict[str, Any]) -> JobMatchRecord:
    normalized = normalize_ai_match(ai_match)
    return JobMatchRecord(
        id=uuid4().hex,
        job_id=job_id,
        profile_hash=profile_hash,
        matcher_version=normalized["version"],
        cache_key=normalized["cacheKey"],
        score=normalized["score"],
        source=normalized["source"],
        confidence=normalized["confidence"],
        breakdown=normalized["breakdown"],
        reasons=normalized["reasons"],
        gaps=normalized["gaps"],
        heuristic_score=normalized["heuristicScore"],
        openclaw_error=normalized.get("openclawError"),
        created_at=parse_match_updated_at(ai_match) or datetime.now(UTC),
    )


def normalize_ai_match(
    ai_match: dict[str, Any],
    fallback_updated_at: datetime | None = None,
) -> dict[str, Any]:
    score = clamp_int(ai_match.get("score"), 0)
    updated_at = (
        str(ai_match.get("updatedAt") or "").strip()
        or (fallback_updated_at or datetime.now(UTC)).isoformat()
    )
    normalized = {
        "version": str(ai_match.get("version") or MATCHER_VERSION),
        "cacheKey": str(ai_match.get("cacheKey") or ""),
        "source": str(ai_match.get("source") or "openclaw"),
        "score": score,
        "confidence": str(ai_match.get("confidence") or "low"),
        "breakdown": ai_match.get("breakdown") if isinstance(ai_match.get("breakdown"), dict) else {},
        "reasons": normalize_string_list(ai_match.get("reasons")),
        "gaps": normalize_string_list(ai_match.get("gaps")),
        "heuristicScore": clamp_int(ai_match.get("heuristicScore"), score),
        "updatedAt": updated_at,
    }
    if ai_match.get("openclawError"):
        normalized["openclawError"] = str(ai_match["openclawError"])[:240]
    return normalized


def match_record_to_ai_match(record: JobMatchRecord) -> dict[str, Any]:
    ai_match = {
        "version": record.matcher_version,
        "cacheKey": record.cache_key,
        "source": record.source,
        "score": record.score,
        "confidence": record.confidence,
        "breakdown": record.breakdown,
        "reasons": record.reasons,
        "gaps": record.gaps,
        "heuristicScore": record.heuristic_score,
        "updatedAt": serialize_datetime(record.created_at),
    }
    if record.openclaw_error:
        ai_match["openclawError"] = record.openclaw_error
    return ai_match


def parse_match_updated_at(ai_match: dict[str, Any]) -> datetime | None:
    value = ai_match.get("updatedAt")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.astimezone(UTC).isoformat()


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:180] for item in value if str(item).strip()]


def clamp_int(value: Any, default: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))
