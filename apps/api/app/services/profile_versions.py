from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.profile import ProfilePayload, ProfileRecord, ProfileVersionRecord


MEANINGFUL_PROFILE_FIELDS = (
    "name",
    "current_role",
    "desired_role",
    "location",
    "work_format",
    "headline",
    "linkedin",
    "github",
    "portfolio",
    "personal_site",
    "experience",
    "skills",
    "education",
    "job_preferences",
    "dealbreakers",
    "additional_notes",
    "documents",
    "resume_data_url",
)


def profile_completeness(profile: ProfilePayload) -> int:
    return sum(
        bool(str(getattr(profile, field_name, "")).strip())
        for field_name in MEANINGFUL_PROFILE_FIELDS
    )


def is_suspicious_profile_replacement(
    current: ProfilePayload,
    replacement: ProfilePayload,
) -> bool:
    current_score = profile_completeness(current)
    replacement_score = profile_completeness(replacement)
    return (
        current_score >= 3
        and replacement_score < current_score
        and replacement_score <= max(1, current_score // 3)
    )


def record_profile_version(
    db: Session,
    profile: ProfileRecord,
    *,
    reason: str,
) -> None:
    db.add(
        ProfileVersionRecord(
            profile_id=profile.id,
            data=dict(profile.data),
            reason=reason,
        )
    )
