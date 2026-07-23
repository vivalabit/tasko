from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import job_search as job_search_api
from app.core.database import Base, get_db
from app.core.settings import Settings, get_settings
from app.main import app
from app.models.jobs import StoredJobRecord
from app.models.parsers import ParsedJob, ParserSearchResponse
from app.services import job_search_execution
from app.services.job_search_execution import AI_CONSENT_WARNING, parsed_job_id
from app.services.vacancy_search import VacancySearchRunResult


@dataclass
class ApiContext:
    client: TestClient
    sessions: sessionmaker[Session]
    settings: Settings


@pytest.fixture
def api_context() -> Generator[ApiContext, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with sessions() as db:
            yield db

    settings = Settings(
        app_env="local",
        database_url="sqlite://",
        ai_consent_version="job-search-test-v1",
    )
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield ApiContext(
            client=TestClient(app),
            sessions=sessions,
            settings=settings,
        )
    finally:
        app.dependency_overrides.clear()


class FakeRunner:
    def __init__(self, result: VacancySearchRunResult) -> None:
        self.result = result
        self.requests = []

    def run(self, **kwargs) -> VacancySearchRunResult:
        self.requests.append(kwargs)
        return self.result


def test_manual_run_accepts_inline_config_without_creating_schedule(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = {"X-Rufina-Owner-Id": "manual-owner"}
    job = parsed_job(
        title="Manual Backend Engineer",
        url="https://www.linkedin.com/jobs/view/manual-1",
    )
    runner = FakeRunner(
        VacancySearchRunResult(
            jobs=[job],
            source_results={"linkedin": completed_response("linkedin", [job])},
            source_errors={},
        )
    )
    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )

    response = api_context.client.post(
        "/job-search/run",
        headers=headers,
        json={
            "config": {
                "name": "Unsaved manual search",
                "filters": {
                    "keywords": "Backend Engineer",
                    "resultsLimit": 15,
                    "deduplicate": True,
                },
            },
            "sources": ["linkedin"],
            "aiAnalysisEnabled": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduleId"] is None
    assert payload["runType"] == "manual"
    assert payload["jobsFound"] == 1
    assert payload["jobsAdded"] == 1
    assert payload["configSnapshot"]["name"] == "Unsaved manual search"
    assert runner.requests[0]["wait_for_snapshots"] is True
    assert runner.requests[0]["request"].results_limit == 15
    assert api_context.client.get("/job-search/schedules", headers=headers).json() == []
    assert [record.data["title"] for record in stored_jobs(
        api_context.sessions,
        owner_id="manual-owner",
    )] == ["Manual Backend Engineer"]


def test_run_now_persists_jobs_snapshot_and_no_consent_warning(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_a = {"X-Rufina-Owner-Id": "owner-a"}
    owner_b = {"X-Rufina-Owner-Id": "owner-b"}
    job = parsed_job(
        title="Platform Engineer",
        url="https://www.linkedin.com/jobs/view/123?trackingId=ignored",
    )
    runner = FakeRunner(
        VacancySearchRunResult(
            jobs=[job],
            source_results={"linkedin": completed_response("linkedin", [job])},
            source_errors={},
        )
    )
    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )
    config_id, schedule_id = create_search(
        api_context.client,
        owner_a,
        filters={
            "keywords": "Platform Engineer",
            "location": "Zurich",
            "resultsLimit": 25,
        },
    )

    response = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=owner_a,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scheduleId"] == schedule_id
    assert payload["runType"] == "manual"
    assert payload["status"] == "completed"
    assert payload["jobsFound"] == 1
    assert payload["jobsAdded"] == 1
    assert payload["warning"] == AI_CONSENT_WARNING
    assert payload["configSnapshot"]["id"] == config_id
    assert payload["configSnapshot"]["filters"] == {
        "keywords": "Platform Engineer",
        "location": "Zurich",
        "resultsLimit": 25,
    }
    assert runner.requests[0]["wait_for_snapshots"] is True
    assert runner.requests[0]["request"].results_limit == 25

    runs = api_context.client.get("/job-search/runs", headers=owner_a)
    assert runs.status_code == 200
    assert [item["id"] for item in runs.json()] == [payload["id"]]
    assert (
        api_context.client.get(
            "/job-search/runs",
            headers=owner_b,
        ).json()
        == []
    )

    records = stored_jobs(api_context.sessions, owner_id="owner-a")
    assert len(records) == 1
    assert records[0].status == "active"
    assert records[0].data["title"] == "Platform Engineer"
    assert "aiMatch" not in records[0].data


def test_run_now_does_not_restore_existing_or_dismissed_jobs_and_matches_only_new(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = {"X-Rufina-Owner-Id": "dedup-owner"}
    existing = parsed_job(
        title="Existing Engineer",
        url="https://www.linkedin.com/jobs/view/existing",
    )
    dismissed = parsed_job(
        title="Dismissed Engineer",
        url="https://www.linkedin.com/jobs/view/dismissed",
    )
    new = parsed_job(
        title="New Engineer",
        url="https://www.linkedin.com/jobs/view/new",
    )
    existing_id = parsed_job_id(existing, index=0)
    dismissed_id = parsed_job_id(dismissed, index=1)
    with api_context.sessions() as db:
        db.add_all(
            [
                StoredJobRecord(
                    owner_id="dedup-owner",
                    id=existing_id,
                    data={
                        "id": existing_id,
                        "title": existing.title,
                        "company": existing.company,
                        "location": existing.location,
                        "sourceUrl": existing.url,
                    },
                    status="active",
                ),
                StoredJobRecord(
                    owner_id="dedup-owner",
                    id=dismissed_id,
                    data={"id": dismissed_id},
                    status="dismissed",
                ),
            ]
        )
        db.commit()

    result = VacancySearchRunResult(
        jobs=[existing, dismissed, new],
        source_results={"linkedin": completed_response("linkedin", [existing, dismissed, new])},
        source_errors={},
    )
    runner = FakeRunner(result)
    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )
    matched_batches: list[list[dict[str, object]]] = []

    def capture_new_jobs(_db, *, jobs, **_kwargs):
        matched_batches.append(jobs)
        return None

    monkeypatch.setattr(
        job_search_execution,
        "match_new_jobs_if_allowed",
        capture_new_jobs,
    )
    _, schedule_id = create_search(api_context.client, headers)

    first = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=headers,
    )
    second = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["jobsFound"] == 3
    assert first.json()["jobsAdded"] == 1
    assert [job["title"] for job in matched_batches[0]] == ["New Engineer"]
    assert second.status_code == 200
    assert second.json()["jobsAdded"] == 0
    assert matched_batches[1] == []

    records = stored_jobs(api_context.sessions, owner_id="dedup-owner")
    assert len(records) == 3
    dismissed_record = next(record for record in records if record.id == dismissed_id)
    assert dismissed_record.status == "dismissed"
    assert dismissed_record.data == {"id": dismissed_id}


def test_run_now_persists_partial_source_failure(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = {"X-Rufina-Owner-Id": "partial-owner"}
    linkedin_job = parsed_job(
        title="Resilient Search Result",
        url="https://www.linkedin.com/jobs/view/partial-1",
    )
    runner = FakeRunner(
        VacancySearchRunResult(
            jobs=[linkedin_job],
            source_results={"linkedin": completed_response("linkedin", [linkedin_job])},
            source_errors={"indeed": "Indeed snapshot failed"},
        )
    )
    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )
    _, schedule_id = create_search(api_context.client, headers)

    response = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["jobsFound"] == 1
    assert response.json()["jobsAdded"] == 1
    assert response.json()["sourceErrors"] == {"indeed": "Indeed snapshot failed"}
    assert len(stored_jobs(api_context.sessions, owner_id="partial-owner")) == 1


def create_search(
    client: TestClient,
    headers: dict[str, str],
    *,
    filters: dict[str, object] | None = None,
) -> tuple[str, str]:
    config_response = client.post(
        "/job-search/configs",
        headers=headers,
        json={
            "name": "Automatic Zurich search",
            "filters": filters
            or {
                "keywords": "Software Engineer",
                "location": "Zurich",
            },
        },
    )
    assert config_response.status_code == 201
    config_id = config_response.json()["id"]
    schedule_response = client.post(
        "/job-search/schedules",
        headers=headers,
        json={
            "name": "Every morning",
            "configId": config_id,
            "sources": ["linkedin", "indeed"],
            "frequency": "daily",
            "weekdays": [],
            "localTime": "08:00:00",
            "timezone": "Europe/Zurich",
            "aiAnalysisEnabled": True,
            "enabled": True,
        },
    )
    assert schedule_response.status_code == 201
    return config_id, schedule_response.json()["id"]


def parsed_job(*, title: str, url: str) -> ParsedJob:
    return ParsedJob(
        source="linkedin",
        title=title,
        company="Rufina Test AG",
        location="Zurich",
        url=url,
        employment_type="Full-time",
        seniority="Mid-Senior level",
        description=f"{title} description",
    )


def completed_response(
    source: str,
    jobs: list[ParsedJob],
) -> ParserSearchResponse:
    return ParserSearchResponse(
        parser=source,
        status="completed",
        search_url=f"https://example.test/{source}",
        jobs=jobs,
    )


def stored_jobs(
    sessions: sessionmaker[Session],
    *,
    owner_id: str,
) -> list[StoredJobRecord]:
    with sessions() as db:
        return list(
            db.scalars(
                select(StoredJobRecord)
                .where(StoredJobRecord.owner_id == owner_id)
                .order_by(StoredJobRecord.id)
            ).all()
        )
