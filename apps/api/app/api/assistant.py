from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.core.settings import Settings, get_settings
from app.models.applications import StoredApplicationRecord
from app.models.assistant import (
    AssistantApplicationContext,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantJobContext,
)
from app.models.jobs import StoredJobRecord
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.assistant import (
    OpenClawAssistantError,
    OpenClawAssistantTimeoutError,
    run_openclaw_assistant,
)

router = APIRouter()


@router.post("/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(
    request: AssistantChatRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AssistantChatResponse:
    if not settings.openclaw_assistant_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenClaw assistant is disabled",
        )

    profile = load_profile(db)
    job = load_job_context(db, request)
    application = load_application_context(db, request)
    if application:
        job = application.job

    try:
        message, session_id = await run_openclaw_assistant(
            thread_id=request.thread_id,
            message=request.message,
            context_kind=request.context_kind,
            profile=profile,
            job=job,
            application=application,
            command=settings.openclaw_command,
            agent_id=settings.openclaw_assistant_agent_id,
            thinking=settings.openclaw_assistant_thinking,
            timeout_seconds=settings.openclaw_assistant_timeout_seconds,
        )
    except OpenClawAssistantTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except OpenClawAssistantError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return AssistantChatResponse(
        message=message,
        metadata={
            "sessionId": session_id,
            "contextKind": request.context_kind,
            "contextId": request.context_id,
        },
    )


def load_profile(db: Session) -> ProfilePayload:
    try:
        record = db.get(ProfileRecord, "default")
        return ProfilePayload.model_validate(record.data) if record else ProfilePayload()
    except (SQLAlchemyError, ValidationError):
        return ProfilePayload()


def load_job_context(
    db: Session,
    request: AssistantChatRequest,
) -> AssistantJobContext | None:
    if request.context_kind != "job":
        return request.job

    try:
        record = db.get(StoredJobRecord, request.context_id) if request.context_id else None
        if record:
            return AssistantJobContext.model_validate(record.data)
    except (SQLAlchemyError, ValidationError):
        pass

    return request.job


def load_application_context(
    db: Session,
    request: AssistantChatRequest,
) -> AssistantApplicationContext | None:
    if request.context_kind != "application":
        return request.application

    try:
        record = (
            db.get(StoredApplicationRecord, request.context_id)
            if request.context_id
            else None
        )
        if record:
            return AssistantApplicationContext.model_validate(record.data)
    except (SQLAlchemyError, ValidationError):
        pass

    return request.application
