from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import assistant as assistant_api
from app.core.database import Base, get_db
from app.core.settings import Settings, get_settings
from app.models.applications import CandidateConfirmationRecord
from app.main import app
from app.models.assistant import AppliedAssistantActionRecord
from app.models.conversations import ConversationRecord
from app.models.documents import DocumentRecord, DocumentTemplateRecord
from app.models.jobs import JobMatchRecord
from app.models.privacy import AiPrivacySettingsRecord
from app.models.profile import CandidateMatchSnapshotRecord, ProfilePayload, ProfileRecord
from app.services.ai_privacy import cleanup_expired_ai_data


def privacy_client() -> tuple[TestClient, sessionmaker[Session]]:
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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        ai_consent_version="privacy-v1",
        openclaw_assistant_enabled=True,
    )
    return TestClient(app), testing_session_local


def test_ai_calls_require_current_server_side_consent(monkeypatch) -> None:
    calls = 0

    async def run_assistant(**_kwargs):
        nonlocal calls
        calls += 1
        return "Generated response", "session-privacy"

    monkeypatch.setattr(assistant_api, "generate_assistant_with_facade", run_assistant)
    client, testing_session_local = privacy_client()
    headers = {"X-Rufina-Owner-Id": "privacy-owner"}
    with testing_session_local() as db:
        db.add(ProfileRecord(id="default", data=ProfilePayload().model_dump()))
        db.commit()

    try:
        initial = client.get("/privacy/ai-consent", headers=headers)
        denied = client.post(
            "/assistant/chat",
            headers=headers,
            json={
                "threadId": "privacy-thread",
                "message": "Review my profile",
                "contextKind": "profile",
            },
        )
        denied_match = client.post(
            "/jobs/ai-match",
            headers=headers,
            json={"jobs": []},
        )
        denied_resume_import = client.post(
            "/profile/import-experience-from-resume",
            headers=headers,
            json={"resume_file_name": "resume.txt", "resume_data_url": ""},
        )
        stale = client.put(
            "/privacy/ai-consent",
            headers=headers,
            json={
                "version": "privacy-v0",
                "backend": "openclaw_codex",
                "retentionDays": 7,
            },
        )
        granted = client.put(
            "/privacy/ai-consent",
            headers=headers,
            json={
                "version": "privacy-v1",
                "backend": "openclaw_codex",
                "retentionDays": 7,
            },
        )
        allowed = client.post(
            "/assistant/chat",
            headers=headers,
            json={
                "threadId": "privacy-thread",
                "message": "Review my profile",
                "contextKind": "profile",
            },
        )
        retention = client.put(
            "/privacy/ai-retention",
            headers=headers,
            json={"retentionDays": 3},
        )
        app.dependency_overrides[get_settings] = lambda: Settings(
            ai_consent_version="privacy-v2",
            openclaw_assistant_enabled=True,
        )
        denied_after_version_change = client.post(
            "/assistant/chat",
            headers=headers,
            json={
                "threadId": "privacy-thread",
                "message": "Review my profile again",
                "contextKind": "profile",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert initial.status_code == 200
    assert initial.json()["providerName"] == "OpenAI via OpenClaw/Codex"
    assert initial.json()["currentBackend"] == "openclaw_codex"
    assert initial.json()["consentBackend"] is None
    assert initial.json()["hasCurrentConsent"] is False
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "ai_consent_required"
    assert denied_match.status_code == 403
    assert denied_resume_import.status_code == 403
    assert calls == 1
    assert stale.status_code == 409
    assert granted.status_code == 200
    assert granted.json()["hasCurrentConsent"] is True
    assert granted.json()["consentBackend"] == "openclaw_codex"
    assert granted.json()["retentionDays"] == 7
    assert granted.json()["consentedAt"]
    assert allowed.status_code == 200
    assert retention.status_code == 200
    assert retention.json()["retentionDays"] == 3
    assert denied_after_version_change.status_code == 403
    assert calls == 1

    with testing_session_local() as db:
        record = db.get(AiPrivacySettingsRecord, "privacy-owner")
        assert record is not None
        assert record.consent_version == "privacy-v1"
        assert record.consent_backend == "openclaw_codex"
        assert record.last_ai_activity_at is not None
        assert record.ai_data_expires_at is not None
        assert record.ai_data_expires_at - record.last_ai_activity_at == timedelta(days=3)


def test_ai_consent_is_invalidated_when_backend_changes() -> None:
    client, testing_session_local = privacy_client()
    headers = {"X-Rufina-Owner-Id": "backend-consent-owner"}

    try:
        granted = client.put(
            "/privacy/ai-consent",
            headers=headers,
            json={
                "version": "privacy-v1",
                "backend": "openclaw_codex",
                "retentionDays": 30,
            },
        )
        app.dependency_overrides[get_settings] = lambda: Settings(
            ai_backend_mode="openai_api",
            openai_api_key="test-key",
            ai_consent_version="privacy-v1",
        )
        after_switch = client.get("/privacy/ai-consent", headers=headers)
        stale_route = client.put(
            "/privacy/ai-consent",
            headers=headers,
            json={
                "version": "privacy-v1",
                "backend": "openclaw_codex",
                "retentionDays": 30,
            },
        )
        renewed = client.put(
            "/privacy/ai-consent",
            headers=headers,
            json={
                "version": "privacy-v1",
                "backend": "openai_api",
                "retentionDays": 30,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert granted.json()["hasCurrentConsent"] is True
    assert after_switch.status_code == 200
    assert after_switch.json()["providerName"] == "OpenAI Responses API"
    assert after_switch.json()["currentBackend"] == "openai_api"
    assert after_switch.json()["consentBackend"] == "openclaw_codex"
    assert after_switch.json()["hasCurrentConsent"] is False
    assert stale_route.status_code == 409
    assert stale_route.json()["detail"] == {
        "code": "ai_consent_backend_mismatch",
        "requiredBackend": "openai_api",
        "providerName": "OpenAI Responses API",
    }
    assert renewed.status_code == 200
    assert renewed.json()["consentBackend"] == "openai_api"
    assert renewed.json()["hasCurrentConsent"] is True

    with testing_session_local() as db:
        record = db.get(AiPrivacySettingsRecord, "backend-consent-owner")
        assert record is not None
        assert record.consent_backend == "openai_api"


def test_expired_ttl_deletes_only_the_owners_ai_data() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    now = datetime.now(UTC)

    with testing_session_local() as db:
        for owner_id, expired in (("expired-owner", True), ("active-owner", False)):
            db.add_all(
                [
                    AiPrivacySettingsRecord(
                        owner_id=owner_id,
                        consent_version="privacy-v1",
                        consent_backend="openclaw_codex",
                        consented_at=now - timedelta(days=2),
                        retention_days=1,
                        last_ai_activity_at=now - timedelta(days=2),
                        ai_data_expires_at=(
                            now - timedelta(days=1)
                            if expired
                            else now + timedelta(days=1)
                        ),
                        updated_at=now,
                    ),
                    ConversationRecord(
                        id=f"conversation-{owner_id}",
                        owner_id=owner_id,
                        title="AI conversation",
                        context_kind="profile",
                        context_id="",
                        archived=False,
                        created_at=now,
                        updated_at=now,
                    ),
                    DocumentRecord(
                        id=f"document-{owner_id}",
                        owner_id=owner_id,
                        type="tailored_resume",
                        title="AI document",
                        current_version=1,
                        created_at=now,
                        updated_at=now,
                    ),
                    AppliedAssistantActionRecord(
                        id=f"action-{owner_id}",
                        owner_id=owner_id,
                        action_type="update_profile_field",
                        result={},
                        applied_at=now,
                    ),
                    CandidateMatchSnapshotRecord(
                        id=f"snapshot-{owner_id}",
                        owner_id=owner_id,
                        profile_input_hash="a" * 64,
                        profile_hash="b" * 64,
                        matcher_version="ai-match-v3",
                        source="openclaw_codex",
                        data={},
                        provider_error=None,
                        created_at=now,
                    ),
                    JobMatchRecord(
                        id=f"match-{owner_id}",
                        owner_id=owner_id,
                        job_id="job-privacy",
                        profile_hash="b" * 64,
                        matcher_version="ai-match-v3",
                        cache_key=f"cache-{owner_id}",
                        score=80,
                        source="openclaw_codex",
                        confidence="high",
                        breakdown={},
                        reasons=[],
                        gaps=[],
                        heuristic_score=75,
                        provider_error=None,
                        created_at=now,
                    ),
                    DocumentTemplateRecord(
                        id=f"template-{owner_id}",
                        owner_id=owner_id,
                        type="tailored_resume",
                        name="Source CV",
                        file_name="resume.docx",
                        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        content_sha256=owner_id.ljust(64, "0")[:64],
                        content=b"source",
                        extracted_text="Candidate-authored source",
                        created_at=now,
                        updated_at=now,
                    ),
                    CandidateConfirmationRecord(
                        application_id=f"application-{owner_id}",
                        question_id="leadership",
                        owner_id=owner_id,
                        requirement="Leadership",
                        response="yes",
                        example_text="Led a verified project",
                        blocking=True,
                        updated_at=now,
                    ),
                ]
            )
        db.commit()

        expired_owners, deleted_records = cleanup_expired_ai_data(db, now=now)

        assert expired_owners == 1
        assert deleted_records == 5
        assert db.get(ConversationRecord, "conversation-expired-owner") is None
        assert db.get(DocumentRecord, "document-expired-owner") is None
        assert db.get(JobMatchRecord, "match-expired-owner") is None
        assert db.get(DocumentTemplateRecord, "template-expired-owner") is not None
        assert db.get(
            CandidateConfirmationRecord,
            ("application-expired-owner", "leadership"),
        ) is not None
        assert db.get(ConversationRecord, "conversation-active-owner") is not None
        assert db.get(DocumentRecord, "document-active-owner") is not None
        assert db.get(JobMatchRecord, "match-active-owner") is not None
        expired_settings = db.get(AiPrivacySettingsRecord, "expired-owner")
        assert expired_settings is not None
        assert expired_settings.consent_version == "privacy-v1"
        assert expired_settings.ai_data_expires_at is None


def test_revoke_consent_deletes_owner_ai_data_but_preserves_other_owners() -> None:
    client, testing_session_local = privacy_client()
    now = datetime.now(UTC)
    with testing_session_local() as db:
        for owner_id in ("delete-owner", "keep-owner"):
            db.add_all(
                [
                    AiPrivacySettingsRecord(
                        owner_id=owner_id,
                        consent_version="privacy-v1",
                        consent_backend="openclaw_codex",
                        consented_at=now,
                        retention_days=30,
                        last_ai_activity_at=now,
                        ai_data_expires_at=now + timedelta(days=30),
                        updated_at=now,
                    ),
                    ConversationRecord(
                        id=f"conversation-{owner_id}",
                        owner_id=owner_id,
                        title="AI conversation",
                        context_kind="profile",
                        context_id="",
                        archived=False,
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )
        db.commit()

    try:
        revoked = client.delete(
            "/privacy/ai-consent",
            headers={"X-Rufina-Owner-Id": "delete-owner"},
        )
    finally:
        app.dependency_overrides.clear()

    assert revoked.status_code == 204
    with testing_session_local() as db:
        deleted_settings = db.get(AiPrivacySettingsRecord, "delete-owner")
        assert deleted_settings is not None
        assert deleted_settings.consent_version is None
        assert deleted_settings.consent_backend is None
        assert deleted_settings.consented_at is None
        assert db.get(ConversationRecord, "conversation-delete-owner") is None
        assert db.get(ConversationRecord, "conversation-keep-owner") is not None
