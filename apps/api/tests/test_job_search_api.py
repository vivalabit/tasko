from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import job_search as job_search_api
from app.core.database import Base, get_db
from app.main import app


def test_job_search_config_and_schedule_crud_is_owner_scoped(
    monkeypatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session_local() as db:
            yield db

    now = datetime(2026, 7, 20, 4, 0, tzinfo=UTC)
    monkeypatch.setattr(job_search_api, "utc_now", lambda: now)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    owner_a = {"X-Tasko-Owner-Id": "owner-a"}
    owner_b = {"X-Tasko-Owner-Id": "owner-b"}

    try:
        create_config = client.post(
            "/job-search/configs",
            headers=owner_a,
            json={
                "name": " Zurich product roles ",
                "filters": {"keywords": "Product Manager", "location": "Zurich"},
            },
        )
        assert create_config.status_code == 201
        config = create_config.json()
        config_id = config["id"]
        assert config["name"] == "Zurich product roles"

        assert (
            client.get(
                f"/job-search/configs/{config_id}",
                headers=owner_b,
            ).status_code
            == 404
        )
        assert client.get("/job-search/configs", headers=owner_b).json() == []
        assert (
            client.post(
                "/job-search/schedules",
                headers=owner_b,
                json=schedule_request(config_id=config_id, name="Foreign config"),
            ).status_code
            == 404
        )

        update_config = client.patch(
            f"/job-search/configs/{config_id}",
            headers=owner_a,
            json={"name": "Zurich PM roles"},
        )
        assert update_config.status_code == 200
        assert update_config.json()["name"] == "Zurich PM roles"

        invalid_source = client.post(
            "/job-search/schedules",
            headers=owner_a,
            json={
                **schedule_request(config_id=config_id, name="Invalid source"),
                "sources": ["monster"],
            },
        )
        assert invalid_source.status_code == 422
        invalid_days = client.post(
            "/job-search/schedules",
            headers=owner_a,
            json={
                **schedule_request(config_id=config_id, name="Invalid days"),
                "weekdays": [],
            },
        )
        assert invalid_days.status_code == 422

        first_schedule = client.post(
            "/job-search/schedules",
            headers=owner_a,
            json=schedule_request(config_id=config_id, name="Morning search"),
        )
        second_schedule = client.post(
            "/job-search/schedules",
            headers=owner_a,
            json=schedule_request(config_id=config_id, name="Second search"),
        )
        assert first_schedule.status_code == 201
        assert second_schedule.status_code == 201
        first = first_schedule.json()
        first_id = first["id"]
        second_id = second_schedule.json()["id"]
        assert first["configId"] == config_id
        assert first["sources"] == ["linkedin", "indeed", "jobs_ch"]
        assert parse_datetime(first["nextRunAt"]) == datetime(
            2026,
            7,
            20,
            5,
            30,
            tzinfo=UTC,
        )
        assert len(client.get("/job-search/schedules", headers=owner_a).json()) == 2
        assert (
            client.get(
                f"/job-search/schedules/{first_id}",
                headers=owner_b,
            ).status_code
            == 404
        )

        blocked_delete = client.delete(
            f"/job-search/configs/{config_id}",
            headers=owner_a,
        )
        assert blocked_delete.status_code == 409
        assert blocked_delete.json()["detail"] == "Config is used by one or more schedules"

        changed_time = client.patch(
            f"/job-search/schedules/{first_id}",
            headers=owner_a,
            json={"localTime": "08:30:00"},
        )
        assert parse_datetime(changed_time.json()["nextRunAt"]) == datetime(
            2026,
            7,
            20,
            6,
            30,
            tzinfo=UTC,
        )
        changed_timezone = client.patch(
            f"/job-search/schedules/{first_id}",
            headers=owner_a,
            json={"timezone": "UTC"},
        )
        assert parse_datetime(changed_timezone.json()["nextRunAt"]) == datetime(
            2026,
            7,
            20,
            8,
            30,
            tzinfo=UTC,
        )
        changed_days = client.patch(
            f"/job-search/schedules/{first_id}",
            headers=owner_a,
            json={"weekdays": [1]},
        )
        assert parse_datetime(changed_days.json()["nextRunAt"]) == datetime(
            2026,
            7,
            21,
            8,
            30,
            tzinfo=UTC,
        )

        disabled = client.patch(
            f"/job-search/schedules/{first_id}",
            headers=owner_a,
            json={"enabled": False},
        )
        assert disabled.status_code == 200
        assert disabled.json()["nextRunAt"] is None

        assert (
            client.delete(
                f"/job-search/schedules/{first_id}",
                headers=owner_a,
            ).status_code
            == 204
        )
        assert (
            client.delete(
                f"/job-search/schedules/{second_id}",
                headers=owner_a,
            ).status_code
            == 204
        )
        assert (
            client.delete(
                f"/job-search/configs/{config_id}",
                headers=owner_a,
            ).status_code
            == 204
        )
        assert client.get("/job-search/configs", headers=owner_a).json() == []
    finally:
        app.dependency_overrides.clear()


def schedule_request(*, config_id: str, name: str) -> dict[str, object]:
    return {
        "name": name,
        "configId": config_id,
        "sources": ["linkedin", "indeed", "linkedin", "jobs_ch"],
        "frequency": "selected_days",
        "weekdays": [0, 2, 4],
        "localTime": "07:30:00",
        "timezone": "Europe/Zurich",
        "aiAnalysisEnabled": True,
        "enabled": True,
    }


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
