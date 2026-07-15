from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.conversations import MessageRecord


def test_conversations_are_stored_archived_restored_and_deleted() -> None:
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
    client = TestClient(app)
    conversation = {
        "title": "Prepare for Figma interview",
        "contextKind": "job",
        "contextId": "job-figma",
        "openClawSessionKey": "agent:tasko-assistant:session-one",
        "messages": [
            {
                "id": "message-user-one",
                "role": "user",
                "content": "Help me prepare",
                "createdAt": "2026-07-15T10:00:00Z",
            },
            {
                "id": "message-assistant-one",
                "role": "assistant",
                "content": "Start with the role requirements.",
                "source": "openclaw",
                "status": "complete",
                "createdAt": "2026-07-15T10:00:01Z",
            },
        ],
    }

    try:
        created = client.put("/assistant/conversations/conversation-one", json=conversation)
        listed = client.get("/assistant/conversations")
        context_updated = client.patch(
            "/assistant/conversations/conversation-one",
            json={"contextKind": "application", "contextId": "application-one"},
        )
        message_updated = client.put(
            "/assistant/conversations/conversation-one/messages/message-assistant-one",
            json={
                "role": "assistant",
                "content": "Updated interview plan.",
                "source": "openclaw",
                "status": "complete",
            },
        )
        archived = client.patch(
            "/assistant/conversations/conversation-one",
            json={"archived": True},
        )
        active_after_archive = client.get("/assistant/conversations")
        archived_list = client.get("/assistant/conversations?archived=true")
        restored = client.patch(
            "/assistant/conversations/conversation-one",
            json={"archived": False},
        )
        deleted = client.delete("/assistant/conversations/conversation-one")

        with testing_session_local() as db:
            message_count = db.scalar(select(func.count()).select_from(MessageRecord))
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 200
    assert created.json()["openClawSessionKey"] == "agent:tasko-assistant:session-one"
    assert [message["role"] for message in created.json()["messages"]] == ["user", "assistant"]
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Prepare for Figma interview"
    assert context_updated.json()["contextKind"] == "application"
    assert context_updated.json()["contextId"] == "application-one"
    assert message_updated.json()["content"] == "Updated interview plan."
    assert archived.json()["archived"] is True
    assert active_after_archive.json() == []
    assert archived_list.json()[0]["id"] == "conversation-one"
    assert restored.json()["archived"] is False
    assert deleted.status_code == 204
    assert message_count == 0


def test_message_id_cannot_be_reused_across_conversations() -> None:
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
    client = TestClient(app)
    payload = {
        "title": "Conversation",
        "contextKind": "profile",
        "messages": [
            {
                "id": "shared-message-id",
                "role": "user",
                "content": "Hello",
                "createdAt": "2026-07-15T10:00:00Z",
            }
        ],
    }

    try:
        first = client.put("/assistant/conversations/first", json=payload)
        second = client.put("/assistant/conversations/second", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 409
