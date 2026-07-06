from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app


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
