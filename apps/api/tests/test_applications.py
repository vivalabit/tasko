from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.applications import CandidateConfirmationRecord
from app.models.jobs import JobMatchRecord
from app.services.ai_match import MATCHER_VERSION
from app.services.job_match_store import APPLICATION_GUIDE_STORAGE_KEY


def test_applications_and_events_can_be_upserted_and_read() -> None:
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

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        application_payload = {
            "applications": [
                {
                    "id": "application-linkedin-product-designer",
                    "data": {
                        "id": "application-linkedin-product-designer",
                        "status": "applied",
                        "appliedAt": "2026-07-06T10:00:00.000Z",
                        "nextStep": "Follow up in 5 days",
                        "notes": "Moved from Jobs after applying.",
                        "job": {
                            "id": "linkedin-product-designer",
                            "company": "Stripe",
                            "title": "Senior Product Designer",
                            "location": "Remote",
                            "type": "Full-time",
                        },
                    },
                }
            ]
        }
        event_payload = {
            "events": [
                {
                    "id": "application-event-phone-screen",
                    "application_id": "application-linkedin-product-designer",
                    "data": {
                        "id": "application-event-phone-screen",
                        "applicationId": "application-linkedin-product-designer",
                        "type": "screening",
                        "title": "Phone screen",
                        "startsAt": "2026-07-11T08:00:00.000Z",
                        "durationMinutes": 30,
                        "timezone": "Europe/Zurich",
                        "location": "Google Meet",
                        "notes": "",
                    },
                }
            ]
        }

        applications_upsert_response = client.put("/applications", json=application_payload)
        applications_read_response = client.get("/applications")
        events_upsert_response = client.put("/applications/events", json=event_payload)
        events_read_response = client.get("/applications/events")

        assert applications_upsert_response.status_code == 200
        assert applications_read_response.status_code == 200
        assert applications_read_response.json()[0]["id"] == "application-linkedin-product-designer"
        assert applications_read_response.json()[0]["data"]["status"] == "applied"

        assert events_upsert_response.status_code == 200
        assert events_read_response.status_code == 200
        assert events_read_response.json()[0]["application_id"] == "application-linkedin-product-designer"
        assert events_read_response.json()[0]["data"]["type"] == "screening"

        updated_event_payload = {
            "id": "application-event-phone-screen",
            "application_id": "application-linkedin-product-designer",
            "data": {
                **event_payload["events"][0]["data"],
                "status": "completed",
                "outcome": "positive",
            },
        }

        update_event_response = client.patch(
            "/applications/events/application-event-phone-screen",
            json=updated_event_payload,
        )
        delete_event_response = client.delete("/applications/events/application-event-phone-screen")
        events_after_delete_response = client.get("/applications/events")

        assert update_event_response.status_code == 200
        assert update_event_response.json()["data"]["status"] == "completed"
        assert update_event_response.json()["data"]["outcome"] == "positive"
        assert delete_event_response.status_code == 204
        assert events_after_delete_response.status_code == 200
        assert events_after_delete_response.json() == []

        client.put("/applications/events", json=event_payload)
        delete_application_response = client.delete("/applications/application-linkedin-product-designer")
        applications_after_delete_response = client.get("/applications")
        events_after_application_delete_response = client.get("/applications/events")

        assert delete_application_response.status_code == 204
        assert applications_after_delete_response.status_code == 200
        assert applications_after_delete_response.json() == []
        assert events_after_application_delete_response.status_code == 200
        assert events_after_application_delete_response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_candidate_confirmations_are_structured_validated_and_persisted() -> None:
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

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    application_id = "application-confirmations"
    job_id = "job-confirmations"

    try:
        create_response = client.put(
            "/applications",
            json={
                "applications": [
                    {
                        "id": application_id,
                        "data": {
                            "id": application_id,
                            "status": "draft",
                            "job": {
                                "id": job_id,
                                "aiMatch": {
                                    "version": MATCHER_VERSION,
                                    "applicationGuide": {
                                        "clarificationQuestions": [
                                            {
                                                "id": "client-spoof",
                                                "requirement": "Client-controlled requirement",
                                                "blocking": False,
                                            }
                                        ]
                                    },
                                },
                            },
                        },
                    }
                ]
            },
        )
        assert create_response.status_code == 200

        unavailable_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={"confirmations": []},
        )
        assert unavailable_response.status_code == 409
        assert "Stored ai-match-v3 is required" in unavailable_response.json()["detail"]

        with testing_session_local() as db:
            db.add(
                JobMatchRecord(
                    id="match-confirmations",
                    job_id=job_id,
                    profile_hash="profile-confirmations",
                    matcher_version=MATCHER_VERSION,
                    cache_key="cache-confirmations",
                    score=80,
                    source="openclaw",
                    confidence="high",
                    breakdown={
                        APPLICATION_GUIDE_STORAGE_KEY: {
                            "clarificationQuestions": [
                                {
                                    "id": "python-example",
                                    "requirement": "Production Python",
                                    "question": "Have you run Python in production?",
                                    "blocking": True,
                                },
                                {
                                    "id": "german-level",
                                    "requirement": "German C1",
                                    "question": "Do you speak German at C1 level?",
                                    "blocking": True,
                                },
                                {
                                    "id": "leadership",
                                    "requirement": "Team leadership",
                                    "question": "Have you led a team?",
                                    "blocking": False,
                                },
                            ]
                        }
                    },
                    reasons=[],
                    gaps=[],
                    heuristic_score=80,
                    created_at=datetime.now(UTC),
                )
            )
            db.commit()

        invalid_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={
                "confirmations": [
                    {
                        "questionId": "python-example",
                        "response": "yes",
                        "exampleText": "yes",
                    },
                    {
                        "questionId": "german-level",
                        "response": "no",
                        "exampleText": "",
                    },
                ]
            },
        )
        assert invalid_response.status_code == 422
        assert "meaningful example" in invalid_response.json()["detail"]

        missing_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={"confirmations": []},
        )
        assert missing_response.status_code == 422
        assert "are missing" in missing_response.json()["detail"]

        unknown_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={
                "confirmations": [
                    {
                        "questionId": "client-spoof",
                        "response": "no",
                        "exampleText": "",
                    }
                ]
            },
        )
        assert unknown_response.status_code == 422
        assert "Unknown candidate confirmation" in unknown_response.json()["detail"]

        client_metadata_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={
                "confirmations": [
                    {
                        "questionId": "python-example",
                        "requirement": "Client-controlled requirement",
                        "response": "no",
                        "exampleText": "",
                        "blocking": False,
                    }
                ]
            },
        )
        assert client_metadata_response.status_code == 422

        confirmations = [
            {
                "questionId": "python-example",
                "response": "yes",
                "exampleText": "Built and operated a Python API in production.",
            },
            {
                "questionId": "german-level",
                "response": "no",
                "exampleText": "",
            },
            {
                "questionId": "leadership",
                "response": "partial",
                "exampleText": "Mentored two engineers during a delivery project.",
            },
        ]
        save_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={"confirmations": confirmations},
        )
        read_response = client.get(f"/applications/{application_id}/confirmations")

        assert save_response.status_code == 200
        assert read_response.status_code == 200
        saved_by_id = {item["questionId"]: item for item in read_response.json()}
        assert saved_by_id["python-example"]["response"] == "yes"
        assert saved_by_id["python-example"]["requirement"] == "Production Python"
        assert saved_by_id["python-example"]["blocking"] is True
        assert saved_by_id["python-example"]["exampleText"].startswith("Built and operated")
        assert saved_by_id["python-example"]["updatedAt"]
        assert saved_by_id["german-level"]["response"] == "no"
        assert saved_by_id["german-level"]["exampleText"] == ""
        assert saved_by_id["leadership"]["requirement"] == "Team leadership"
        assert saved_by_id["leadership"]["blocking"] is False

        unchanged_response = client.put(
            f"/applications/{application_id}/confirmations",
            json={"confirmations": confirmations},
        )
        unchanged_by_id = {item["questionId"]: item for item in unchanged_response.json()}
        assert (
            unchanged_by_id["python-example"]["updatedAt"]
            == saved_by_id["python-example"]["updatedAt"]
        )

        delete_response = client.delete(f"/applications/{application_id}")
        assert delete_response.status_code == 204
        with testing_session_local() as db:
            assert db.query(CandidateConfirmationRecord).count() == 0
    finally:
        app.dependency_overrides.clear()
