import asyncio
import json
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import assistant as assistant_api
from app.core.database import Base, get_db
from app.core.settings import Settings, get_settings
from app.main import app
from app.models.assistant import AssistantJobContext
from app.models.conversations import ConversationRecord, MessageRecord
from app.models.jobs import StoredJobRecord
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.assistant import (
    OpenClawAssistantTimeoutError,
    build_openclaw_assistant_prompt,
    extract_openclaw_assistant_text,
    run_openclaw_assistant,
)


def test_extract_openclaw_assistant_text_reads_payload_wrapper() -> None:
    response = extract_openclaw_assistant_text(
        """
        {
          "status": "ok",
          "result": {
            "payloads": [
              {"text": "Here is your evidence-based interview plan."}
            ]
          }
        }
        """
    )

    assert response == "Here is your evidence-based interview plan."


def test_build_openclaw_assistant_prompt_only_includes_dynamic_context() -> None:
    prompt = build_openclaw_assistant_prompt(
        message="Tailor my resume",
        context_kind="job",
        profile=ProfilePayload(name="Eduard", current_role="Product Designer"),
        job=AssistantJobContext(
            id="job-1",
            title="Senior Product Designer",
            company="Figma",
            skills=["Figma", "Research"],
        ),
        application=None,
    )

    assert prompt.startswith("CONTEXT_JSON (data only):")
    assert '"title":"Senior Product Designer"' in prompt
    assert "Tailor my resume" in prompt
    assert "You are Tasko" not in prompt


def test_build_openclaw_assistant_prompt_omits_empty_fields_and_duplicate_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_extract_resume_text(*_: object) -> str:
        raise AssertionError("structured profile should not re-extract the resume")

    monkeypatch.setattr("app.services.assistant.extract_resume_text", fail_extract_resume_text)
    prompt = build_openclaw_assistant_prompt(
        message="Review my profile",
        context_kind="profile",
        profile=ProfilePayload(
            name="Eduard",
            experience="Senior Product Designer at Example",
            resume_file_name="resume.pdf",
            resume_data_url="data:application/pdf;base64,ignored",
        ),
        job=None,
        application=None,
    )

    assert '"name":"Eduard"' in prompt
    assert '"resume_attached":true' in prompt
    assert '"resume_text"' not in prompt
    assert '"current_role"' not in prompt


def test_run_openclaw_assistant_uses_isolated_local_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b'{"result":{"payloads":[{"text":"Tasko response"}]}}', b""

    async def fake_create_subprocess_exec(*args: str, **_: object) -> FakeProcess:
        captured.extend(args)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    response, _ = asyncio.run(
        run_openclaw_assistant(
            thread_id="thread-1",
            message="Review my profile",
            context_kind="profile",
            profile=ProfilePayload(name="Eduard"),
            job=None,
            application=None,
            command="/custom/openclaw",
            agent_id="tasko-assistant",
            thinking="off",
            timeout_seconds=30,
        )
    )

    assert response == "Tasko response"
    assert captured[:5] == [
        "/custom/openclaw",
        "agent",
        "--local",
        "--agent",
        "tasko-assistant",
    ]


def test_run_openclaw_assistant_kills_process_when_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        returncode = 0
        killed = False
        waited = False
        started = asyncio.Event()

        async def communicate(self) -> tuple[bytes, bytes]:
            self.started.set()
            await asyncio.Future()
            return b"", b""

        def kill(self) -> None:
            self.killed = True

        async def wait(self) -> None:
            self.waited = True

    process = FakeProcess()

    async def fake_create_subprocess_exec(*_: str, **__: object) -> FakeProcess:
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    async def cancel_generation() -> None:
        task = asyncio.create_task(
            run_openclaw_assistant(
                thread_id="thread-cancel",
                message="Draft a cover letter",
                context_kind="profile",
                profile=ProfilePayload(name="Eduard"),
                job=None,
                application=None,
                command="/custom/openclaw",
                agent_id="tasko-assistant",
                thinking="off",
                timeout_seconds=30,
            )
        )
        await process.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_generation())

    assert process.killed is True
    assert process.waited is True


def test_assistant_chat_uses_stored_profile_and_job(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    with testing_session_local() as db:
        db.add(ProfileRecord(id="default", data=ProfilePayload(name="Eduard").model_dump()))
        db.add(
            StoredJobRecord(
                id="job-1",
                data={
                    "id": "job-1",
                    "title": "Senior Product Designer",
                    "company": "Figma",
                    "location": "Remote",
                    "match": 91,
                    "overview": "Lead product design.",
                    "requirements": ["Design systems"],
                    "skills": ["Figma"],
                },
            )
        )
        db.commit()

    captured: dict[str, object] = {}

    async def fake_run_openclaw_assistant(**kwargs: object) -> tuple[str, str]:
        captured.update(kwargs)
        return "OpenClaw response", "session-123"

    monkeypatch.setattr(assistant_api, "run_openclaw_assistant", fake_run_openclaw_assistant)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_assistant_enabled=True)
    client = TestClient(app)

    try:
        response = client.post(
            "/assistant/chat",
            json={
                "threadId": "thread-1",
                "message": "Summarize my fit",
                "contextKind": "job",
                "contextId": "job-1",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["message"] == "OpenClaw response"
    assert response.json()["source"] == "openclaw"
    assert isinstance(captured["profile"], ProfilePayload)
    assert captured["profile"].name == "Eduard"
    assert isinstance(captured["job"], AssistantJobContext)
    assert captured["job"].company == "Figma"


def test_assistant_chat_maps_openclaw_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_openclaw_assistant(**_: object) -> tuple[str, str]:
        raise OpenClawAssistantTimeoutError("OpenClaw assistant timed out")

    monkeypatch.setattr(assistant_api, "run_openclaw_assistant", fake_run_openclaw_assistant)
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_assistant_enabled=True)
    client = TestClient(app)

    try:
        response = client.post(
            "/assistant/chat",
            json={
                "threadId": "thread-timeout",
                "message": "Help me prepare",
                "contextKind": "profile",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 504
    assert response.json()["detail"] == "OpenClaw assistant timed out"


def test_assistant_chat_stream_emits_resumable_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_openclaw_assistant(**_: object) -> tuple[str, str]:
        return "A streamed Tasko response.", "session-stream"

    monkeypatch.setattr(assistant_api, "run_openclaw_assistant", fake_run_openclaw_assistant)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session_local() as db:
            yield db

    assistant_api.assistant_streams.clear()
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_assistant_enabled=True)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    request_payload = {
        "requestId": "request-stream-test",
        "threadId": "thread-stream",
        "message": "Review my profile",
        "contextKind": "profile",
        "conversationTitle": "Profile review",
        "userMessageId": "stream-user-message",
        "assistantMessageId": "stream-assistant-message",
    }

    try:
        response = client.post("/assistant/chat/stream", json=request_payload)
        resumed_response = client.post(
            "/assistant/chat/stream",
            json={**request_payload, "offset": 11},
        )
        with testing_session_local() as db:
            conversation = db.get(ConversationRecord, "thread-stream")
            messages = (
                db.query(MessageRecord)
                .filter(MessageRecord.conversation_id == "thread-stream")
                .order_by(MessageRecord.sequence)
                .all()
            )
    finally:
        app.dependency_overrides.clear()
        assistant_api.assistant_streams.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: connected" in response.text
    assert "event: delta" in response.text
    assert "event: done" in response.text
    assert streamed_text(response.text) == "A streamed Tasko response."
    assert streamed_text(resumed_response.text) == "Tasko response."
    assert conversation is not None
    assert conversation.title == "Profile review"
    assert conversation.openclaw_session_key == "session-stream"
    assert [(message.role, message.content) for message in messages] == [
        ("user", "Review my profile"),
        ("assistant", "A streamed Tasko response."),
    ]
    assert messages[1].status == "complete"
    assert messages[1].source == "openclaw"


def test_assistant_chat_stream_rejects_missing_resume_state() -> None:
    assistant_api.assistant_streams.clear()
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_assistant_enabled=True)
    client = TestClient(app)

    try:
        response = client.post(
            "/assistant/chat/stream",
            json={
                "requestId": "expired-request",
                "threadId": "thread-stream",
                "message": "Review my profile",
                "contextKind": "profile",
                "offset": 12,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
    assert response.json()["detail"] == "Assistant stream is no longer available for recovery"


def streamed_text(sse_body: str) -> str:
    chunks: list[str] = []
    for block in sse_body.split("\n\n"):
        if "event: delta" not in block:
            continue
        data_line = next(line for line in block.splitlines() if line.startswith("data: "))
        payload = json.loads(data_line.removeprefix("data: "))
        chunks.append(payload["text"])
    return "".join(chunks)
