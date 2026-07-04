from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.models.profile import ProfilePayload, ProfileRecord

router = APIRouter()

default_profile = ProfilePayload()

legacy_default_profile = {
    "name": "Alex Johnson",
    "current_role": "Senior Product Designer",
    "desired_role": "Design Manager",
    "location": "San Francisco, CA, USA",
    "work_format": "Remote, open to hybrid",
    "headline": (
        "Product designer with 7+ years of experience crafting intuitive B2B and B2C "
        "digital experiences. Combines user empathy with data-driven design to ship "
        "impactful products."
    ),
    "linkedin": "linkedin.com/in/alexjohnson",
    "github": "github.com/alexjohnson",
    "portfolio": "alexjohnson.design",
    "personal_site": "alexjohnson.com",
}


def is_legacy_default_profile(data: dict[str, object]) -> bool:
    return all(data.get(field) == value for field, value in legacy_default_profile.items())


def normalize_profile_record(profile: ProfileRecord, db: Session) -> ProfilePayload:
    if is_legacy_default_profile(profile.data):
        profile.data = default_profile.model_dump()
        db.commit()
        db.refresh(profile)

    return ProfilePayload.model_validate(profile.data)


def get_or_create_profile(db: Session) -> ProfileRecord:
    profile = db.get(ProfileRecord, "default")
    if profile:
        return profile

    profile = ProfileRecord(id="default", data=default_profile.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=ProfilePayload)
def get_profile(db: Session = Depends(get_db)) -> ProfilePayload:
    try:
        profile = get_or_create_profile(db)
        return normalize_profile_record(profile, db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile database is unavailable",
        ) from exc


@router.put("", response_model=ProfilePayload)
def update_profile(payload: ProfilePayload, db: Session = Depends(get_db)) -> ProfilePayload:
    try:
        profile = db.get(ProfileRecord, "default")
        if profile:
            profile.data = payload.model_dump()
        else:
            profile = ProfileRecord(id="default", data=payload.model_dump())
            db.add(profile)

        db.commit()
        db.refresh(profile)
        return ProfilePayload.model_validate(profile.data)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Profile database is unavailable",
        ) from exc
