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
from app.models.jobs import StoredJobRecord
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.assistant import (
    OpenClawAssistantTimeoutError,
    build_openclaw_assistant_prompt,
    extract_openclaw_assistant_text,
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


def test_build_openclaw_assistant_prompt_includes_guardrails_and_context() -> None:
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

    assert "Never invent" in prompt
    assert '"title":"Senior Product Designer"' in prompt
    assert "Tailor my resume" in prompt


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
