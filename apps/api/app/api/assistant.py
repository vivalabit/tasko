import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Literal

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.settings import Settings, get_settings
from app.models.applications import StoredApplicationRecord
from app.models.assistant import (
    AssistantApplicationContext,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantJobContext,
    AssistantStreamRequest,
)
from app.models.jobs import StoredJobRecord
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.assistant import (
    OpenClawAssistantError,
    OpenClawAssistantTimeoutError,
    run_openclaw_assistant,
)

router = APIRouter()

StreamStatus = Literal["generating", "complete", "error", "stopped"]
STREAM_RETENTION_SECONDS = 600


@dataclass
class AssistantStreamState:
    request_id: str
    fingerprint: str
    status: StreamStatus = "generating"
    text: str = ""
    error: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.monotonic)
    updated: asyncio.Event = field(default_factory=asyncio.Event)
    task: asyncio.Task[None] | None = None


assistant_streams: dict[str, AssistantStreamState] = {}


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


@router.post("/chat/stream")
async def stream_chat_with_assistant(
    request: AssistantStreamRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    if not settings.openclaw_assistant_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenClaw assistant is disabled",
        )

    prune_assistant_streams()
    fingerprint = stream_request_fingerprint(request)
    stream = assistant_streams.get(request.request_id)
    if stream and stream.fingerprint != fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requestId is already used by another assistant request",
        )

    if not stream and request.offset:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Assistant stream is no longer available for recovery",
        )

    if not stream:
        profile = load_profile(db)
        job = load_job_context(db, request)
        application = load_application_context(db, request)
        if application:
            job = application.job

        stream = AssistantStreamState(
            request_id=request.request_id,
            fingerprint=fingerprint,
        )
        assistant_streams[request.request_id] = stream
        stream.task = asyncio.create_task(
            generate_assistant_stream(
                stream=stream,
                request=request,
                profile=profile,
                job=job,
                application=application,
                settings=settings,
            )
        )

    start_offset = min(request.offset, len(stream.text))
    return StreamingResponse(
        iterate_assistant_stream(stream, start_offset),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/chat/stream/{request_id}", status_code=status.HTTP_202_ACCEPTED)
async def stop_chat_stream(request_id: str) -> dict[str, str]:
    stream = assistant_streams.get(request_id)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assistant stream was not found",
        )

    if stream.task and not stream.task.done():
        stream.task.cancel()
    if stream.status == "generating":
        update_stream_status(stream, "stopped")
    return {"status": stream.status}


async def generate_assistant_stream(
    *,
    stream: AssistantStreamState,
    request: AssistantStreamRequest,
    profile: ProfilePayload,
    job: AssistantJobContext | None,
    application: AssistantApplicationContext | None,
    settings: Settings,
) -> None:
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
        stream.metadata = {
            "sessionId": session_id,
            "contextKind": request.context_kind,
            "contextId": request.context_id,
        }
        for chunk in split_stream_text(message):
            stream.text += chunk
            touch_stream(stream)
            await asyncio.sleep(0.035)
        update_stream_status(stream, "complete")
    except asyncio.CancelledError:
        update_stream_status(stream, "stopped")
    except OpenClawAssistantTimeoutError:
        stream.error = "OpenClaw assistant timed out"
        update_stream_status(stream, "error")
    except OpenClawAssistantError as exc:
        stream.error = str(exc)
        update_stream_status(stream, "error")
    except Exception:
        stream.error = "Assistant generation failed"
        update_stream_status(stream, "error")


async def iterate_assistant_stream(stream: AssistantStreamState, offset: int):
    cursor = offset
    yield format_sse_event(
        "connected",
        {"requestId": stream.request_id, "offset": cursor},
        event_id=cursor,
    )

    while True:
        stream.updated.clear()
        if len(stream.text) > cursor:
            delta = stream.text[cursor:]
            cursor = len(stream.text)
            yield format_sse_event(
                "delta",
                {"text": delta, "offset": cursor},
                event_id=cursor,
            )

        if stream.status == "complete":
            yield format_sse_event(
                "done",
                {"offset": cursor, "metadata": stream.metadata},
                event_id=cursor,
            )
            return
        if stream.status == "error":
            yield format_sse_event(
                "error",
                {"message": stream.error or "Assistant generation failed", "offset": cursor},
                event_id=cursor,
            )
            return
        if stream.status == "stopped":
            yield format_sse_event("stopped", {"offset": cursor}, event_id=cursor)
            return

        try:
            await asyncio.wait_for(stream.updated.wait(), timeout=10)
        except TimeoutError:
            yield ": keep-alive\n\n"


def split_stream_text(text: str, target_chars: int = 32) -> list[str]:
    parts = re.findall(r"\S+\s*|\s+", text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        current += part
        if len(current) >= target_chars or "\n" in part:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks or [text]


def format_sse_event(event: str, payload: dict[str, object], *, event_id: int) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event_id}\nevent: {event}\ndata: {data}\n\n"


def stream_request_fingerprint(request: AssistantStreamRequest) -> str:
    payload = request.model_dump(by_alias=True, exclude={"offset"})
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def touch_stream(stream: AssistantStreamState) -> None:
    stream.updated_at = time.monotonic()
    stream.updated.set()


def update_stream_status(stream: AssistantStreamState, status_value: StreamStatus) -> None:
    stream.status = status_value
    touch_stream(stream)


def prune_assistant_streams() -> None:
    cutoff = time.monotonic() - STREAM_RETENTION_SECONDS
    expired = [
        request_id
        for request_id, stream in assistant_streams.items()
        if stream.status != "generating" and stream.updated_at < cutoff
    ]
    for request_id in expired:
        assistant_streams.pop(request_id, None)


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
