from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.identity import (
    RequestIdentity,
    bind_request_identity,
    get_request_identity,
)
from app.core.settings import Settings, get_settings
from app.models.documents import utc_now
from app.models.privacy import (
    AiConsentUpdateRequest,
    AiPrivacySettingsPayload,
    AiPrivacySettingsRecord,
    AiRetentionUpdateRequest,
)
from app.services.ai_privacy import (
    delete_ai_data_for_owner,
    has_current_ai_consent,
    privacy_settings_record,
)
from app.services.ai_backend import ai_backend_provider_name

router = APIRouter(dependencies=[Depends(bind_request_identity)])


@router.get("/ai-consent", response_model=AiPrivacySettingsPayload)
def get_ai_privacy_settings(
    identity: RequestIdentity = Depends(get_request_identity),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AiPrivacySettingsPayload:
    try:
        return privacy_payload(
            privacy_settings_record(db, identity.owner_id),
            settings,
        )
    except SQLAlchemyError as exc:
        raise privacy_database_unavailable(exc) from exc


@router.put("/ai-consent", response_model=AiPrivacySettingsPayload)
def grant_ai_consent(
    request: AiConsentUpdateRequest,
    identity: RequestIdentity = Depends(get_request_identity),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AiPrivacySettingsPayload:
    if request.version != settings.ai_consent_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ai_consent_version_mismatch",
                "requiredVersion": settings.ai_consent_version,
            },
        )
    if request.backend != settings.ai_backend_mode:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ai_consent_backend_mismatch",
                "requiredBackend": settings.ai_backend_mode,
                "providerName": ai_backend_provider_name(settings.ai_backend_mode),
            },
        )
    try:
        now = utc_now()
        record = privacy_settings_record(db, identity.owner_id)
        if record is None:
            record = AiPrivacySettingsRecord(
                owner_id=identity.owner_id,
                consent_version=request.version,
                consent_backend=settings.ai_backend_mode,
                consented_at=now,
                retention_days=request.retention_days,
                last_ai_activity_at=None,
                ai_data_expires_at=None,
                updated_at=now,
            )
            db.add(record)
        else:
            record.consent_version = request.version
            record.consent_backend = settings.ai_backend_mode
            record.consented_at = now
            record.retention_days = request.retention_days
            if record.last_ai_activity_at is not None:
                record.ai_data_expires_at = record.last_ai_activity_at + timedelta(
                    days=request.retention_days
                )
            record.updated_at = now
        db.commit()
        db.refresh(record)
        return privacy_payload(record, settings)
    except SQLAlchemyError as exc:
        db.rollback()
        raise privacy_database_unavailable(exc) from exc


@router.put("/ai-retention", response_model=AiPrivacySettingsPayload)
def update_ai_retention(
    request: AiRetentionUpdateRequest,
    identity: RequestIdentity = Depends(get_request_identity),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AiPrivacySettingsPayload:
    try:
        record = privacy_settings_record(db, identity.owner_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI privacy settings were not found",
            )
        record.retention_days = request.retention_days
        if record.last_ai_activity_at is not None:
            record.ai_data_expires_at = record.last_ai_activity_at + timedelta(
                days=request.retention_days
            )
        record.updated_at = utc_now()
        db.commit()
        db.refresh(record)
        return privacy_payload(record, settings)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise privacy_database_unavailable(exc) from exc


@router.delete("/ai-consent", status_code=status.HTTP_204_NO_CONTENT)
def revoke_ai_consent(
    delete_data: bool = Query(default=True, alias="deleteData"),
    identity: RequestIdentity = Depends(get_request_identity),
    db: Session = Depends(get_db),
) -> Response:
    try:
        discard_owner_assistant_streams(identity.owner_id)
        record = privacy_settings_record(db, identity.owner_id)
        if record:
            record.consent_version = None
            record.consent_backend = None
            record.consented_at = None
            record.updated_at = utc_now()
        if delete_data:
            delete_ai_data_for_owner(db, identity.owner_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except SQLAlchemyError as exc:
        db.rollback()
        raise privacy_database_unavailable(exc) from exc


@router.delete("/ai-data", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_data(
    identity: RequestIdentity = Depends(get_request_identity),
    db: Session = Depends(get_db),
) -> Response:
    try:
        discard_owner_assistant_streams(identity.owner_id)
        delete_ai_data_for_owner(db, identity.owner_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except SQLAlchemyError as exc:
        db.rollback()
        raise privacy_database_unavailable(exc) from exc


def privacy_payload(
    record: AiPrivacySettingsRecord | None,
    settings: Settings,
) -> AiPrivacySettingsPayload:
    return AiPrivacySettingsPayload(
        provider_name=ai_backend_provider_name(settings.ai_backend_mode),
        current_backend=settings.ai_backend_mode,
        current_consent_version=settings.ai_consent_version,
        consent_version=record.consent_version if record else None,
        consent_backend=record.consent_backend if record else None,
        consented_at=record.consented_at if record else None,
        has_current_consent=has_current_ai_consent(record, settings),
        retention_days=(record.retention_days if record else 30),
        last_ai_activity_at=record.last_ai_activity_at if record else None,
        ai_data_expires_at=record.ai_data_expires_at if record else None,
    )


def privacy_database_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI privacy settings database is unavailable",
    )


def discard_owner_assistant_streams(owner_id: str) -> None:
    # Imported lazily to avoid a module cycle: assistant routes depend on the
    # consent dependency declared in the privacy service.
    from app.api.assistant import discard_owner_assistant_streams as discard_streams

    discard_streams(owner_id)
