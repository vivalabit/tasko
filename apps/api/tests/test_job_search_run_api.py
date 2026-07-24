from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import job_search as job_search_api
from app.core.database import Base, get_db
from app.core.settings import Settings, get_settings
from app.main import app
from app.models.job_screening import JobScreeningDecisionRecord
from app.models.jobs import StoredJobRecord
from app.models.parsers import ParsedJob, ParserSearchResponse
from app.models.privacy import AiPrivacySettingsRecord
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


class FakeScreeningFacade:
    def __init__(self, decisions_by_title: dict[str, str]) -> None:
        self.decisions_by_title = decisions_by_title
        self.calls: list[list[dict[str, object]]] = []

    def screen(self, _config, jobs):
        self.calls.append(jobs)
        return [
            {
                "id": job["id"],
                "decision": self.decisions_by_title[job["title"]],
                "reasonCode": {
                    "keep": "target_role_match",
                    "reject": "excluded_role",
                    "uncertain": "insufficient_data",
                }[self.decisions_by_title[job["title"]]],
                "matchedRuleIds": [],
                "reason": f"Screened {job['title']}",
            }
            for job in jobs
        ]


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
    assert payload["jobsAlreadyKnown"] == 0
    assert payload["jobsScreened"] == 0
    assert payload["jobsPassed"] == 0
    assert payload["jobsRejected"] == 0
    assert payload["jobsUncertain"] == 0
    assert payload["jobsAdded"] == 1
    assert payload["jobsAnalyzed"] == 0
    assert payload["screeningErrors"] == 0
    assert payload["configSnapshot"]["name"] == "Unsaved manual search"
    assert runner.requests[0]["wait_for_snapshots"] is True
    assert runner.requests[0]["request"].results_limit == 15
    assert api_context.client.get("/job-search/schedules", headers=headers).json() == []
    assert [record.data["title"] for record in stored_jobs(
        api_context.sessions,
        owner_id="manual-owner",
    )] == ["Manual Backend Engineer"]


def test_manual_screening_persists_and_matches_only_keep_and_reuses_cache(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = "screening-owner"
    headers = {"X-Rufina-Owner-Id": owner_id}
    keep = parsed_job(
        title="Target Software Engineer",
        url="https://www.linkedin.com/jobs/view/screening-keep",
    )
    reject = parsed_job(
        title="Rejected Sales Manager",
        url="https://www.linkedin.com/jobs/view/screening-reject",
    )
    uncertain = parsed_job(
        title="Unclear Specialist",
        url="https://www.linkedin.com/jobs/view/screening-uncertain",
    )
    jobs = [keep, reject, uncertain]
    runner = FakeRunner(
        VacancySearchRunResult(
            jobs=jobs,
            source_results={"linkedin": completed_response("linkedin", jobs)},
            source_errors={},
        )
    )
    facade = FakeScreeningFacade(
        {
            keep.title: "keep",
            reject.title: "reject",
            uncertain.title: "uncertain",
        }
    )
    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )
    monkeypatch.setattr(
        job_search_execution,
        "create_job_screening_ai_facade",
        lambda _settings: facade,
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
    grant_ai_consent(api_context, owner_id=owner_id)
    _, schedule_id = create_search(
        api_context.client,
        headers,
        filters=screening_filters(),
    )

    first = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=headers,
    )
    second = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=headers,
    )

    assert first.status_code == 200
    assert first.json()["status"] == "completed"
    assert first.json()["jobsFound"] == 3
    assert first.json()["jobsAlreadyKnown"] == 0
    assert first.json()["jobsScreened"] == 3
    assert first.json()["jobsPassed"] == 1
    assert first.json()["jobsRejected"] == 1
    assert first.json()["jobsUncertain"] == 1
    assert first.json()["jobsAdded"] == 1
    assert first.json()["jobsAnalyzed"] == 1
    assert first.json()["screeningErrors"] == 0
    assert first.json()["warning"] is None
    assert [job["title"] for job in matched_batches[0]] == [keep.title]
    assert [record.data["title"] for record in stored_jobs(
        api_context.sessions,
        owner_id=owner_id,
    )] == [keep.title]
    assert len(facade.calls) == 1
    assert {job["title"] for job in facade.calls[0]} == {
        keep.title,
        reject.title,
        uncertain.title,
    }
    assert set(facade.calls[0][0]) == {
        "id",
        "title",
        "company",
        "location",
        "description",
        "employmentType",
        "seniority",
        "source",
        "postedAt",
        "salaryMin",
        "salaryMax",
        "salaryCurrency",
    }

    assert second.status_code == 200
    assert second.json()["jobsAlreadyKnown"] == 1
    assert second.json()["jobsScreened"] == 2
    assert second.json()["jobsPassed"] == 0
    assert second.json()["jobsRejected"] == 1
    assert second.json()["jobsUncertain"] == 1
    assert second.json()["jobsAdded"] == 0
    assert second.json()["jobsAnalyzed"] == 0
    assert len(facade.calls) == 1
    assert matched_batches[1] == []

    with api_context.sessions() as db:
        decisions = list(
            db.scalars(
                select(JobScreeningDecisionRecord)
                .where(JobScreeningDecisionRecord.owner_id == owner_id)
            ).all()
        )
    assert len(decisions) == 3
    assert {decision.decision for decision in decisions} == {
        "keep",
        "reject",
        "uncertain",
    }


def test_manual_screening_error_is_partial_and_fail_closed(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = "screening-error-owner"
    headers = {"X-Rufina-Owner-Id": owner_id}
    job = parsed_job(
        title="Unchecked Engineer",
        url="https://www.linkedin.com/jobs/view/screening-error",
    )
    runner = FakeRunner(
        VacancySearchRunResult(
            jobs=[job],
            source_results={"linkedin": completed_response("linkedin", [job])},
            source_errors={},
        )
    )

    class FailingScreeningFacade:
        def screen(self, _config, _jobs):
            raise RuntimeError("screening backend unavailable")

    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )
    monkeypatch.setattr(
        job_search_execution,
        "create_job_screening_ai_facade",
        lambda _settings: FailingScreeningFacade(),
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
    grant_ai_consent(api_context, owner_id=owner_id)
    _, schedule_id = create_search(
        api_context.client,
        headers,
        filters=screening_filters(),
    )

    response = api_context.client.post(
        f"/job-search/schedules/{schedule_id}/run",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["jobsScreened"] == 1
    assert payload["jobsPassed"] == 0
    assert payload["jobsRejected"] == 0
    assert payload["jobsUncertain"] == 1
    assert payload["jobsAdded"] == 0
    assert payload["jobsAnalyzed"] == 0
    assert payload["screeningErrors"] == 1
    assert "unverified vacancies were skipped" in payload["warning"]
    assert stored_jobs(api_context.sessions, owner_id=owner_id) == []
    assert matched_batches == [[]]
    with api_context.sessions() as db:
        decision = db.scalar(
            select(JobScreeningDecisionRecord).where(
                JobScreeningDecisionRecord.owner_id == owner_id
            )
        )
    assert decision is not None
    assert decision.decision == "uncertain"
    assert decision.reason_code == "screening_error"


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
    assert payload["jobsAlreadyKnown"] == 0
    assert payload["jobsAdded"] == 1
    assert payload["jobsAnalyzed"] == 0
    assert payload["screeningErrors"] == 0
    assert payload["warning"] == AI_CONSENT_WARNING
    assert payload["configSnapshot"]["id"] == config_id
    normalized_config = payload["configSnapshot"]["filters"]
    assert normalized_config["schemaVersion"] == 2
    assert normalized_config["search"]["keywords"] == "Platform Engineer"
    assert normalized_config["search"]["location"] == "Zurich"
    assert normalized_config["search"]["resultsLimit"] == 25
    assert normalized_config["screening"] == {
        "enabled": False,
        "targetRoles": [],
        "allowedSeniority": [],
        "excludedSeniority": [],
        "hardRules": [],
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


def test_manual_run_accepts_v2_config_and_only_sends_search_to_parser(
    api_context: ApiContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = {"X-Rufina-Owner-Id": "v2-owner"}
    runner = FakeRunner(
        VacancySearchRunResult(
            jobs=[],
            source_results={"linkedin": completed_response("linkedin", [])},
            source_errors={},
        )
    )
    monkeypatch.setattr(
        job_search_api,
        "create_vacancy_search_runner",
        lambda _settings: runner,
    )
    versioned_config = {
        "schemaVersion": 2,
        "search": {
            "keywords": "Product Manager",
            "location": "Zurich",
            "resultsLimit": 100,
        },
        "screening": {
            "enabled": True,
            "targetRoles": ["Product Manager"],
            "allowedSeniority": ["entry", "junior", "associate"],
            "excludedSeniority": ["senior", "lead", "director"],
            "hardRules": [],
        },
    }

    response = api_context.client.post(
        "/job-search/run",
        headers=headers,
        json={
            "config": {
                "name": "Versioned search",
                "filters": versioned_config,
            },
            "sources": ["linkedin"],
            "aiAnalysisEnabled": False,
        },
    )

    assert response.status_code == 200
    parser_request = runner.requests[0]["request"]
    assert parser_request.keywords == "Product Manager"
    assert parser_request.location == "Zurich"
    assert parser_request.results_limit == 100
    assert "screening" not in parser_request.model_dump()
    snapshot = response.json()["configSnapshot"]["filters"]
    assert snapshot["schemaVersion"] == 2
    assert snapshot["search"]["keywords"] == "Product Manager"
    assert snapshot["search"]["location"] == "Zurich"
    assert snapshot["search"]["resultsLimit"] == 100
    assert snapshot["screening"] == versioned_config["screening"]


@pytest.mark.parametrize(
    "screening",
    [
        {"enabled": False, "hardRules": [], "unknown": True},
        {"enabled": "yes", "hardRules": []},
        {
            "enabled": True,
            "hardRules": [
                {
                    "field": "title",
                    "operator": "unsupported",
                    "value": "Python",
                }
            ],
        },
        {
            "enabled": True,
            "allowedSeniority": ["senior"],
            "excludedSeniority": ["senior"],
            "hardRules": [],
        },
        {
            "enabled": True,
            "allowedSeniority": ["principal"],
            "hardRules": [],
        },
    ],
)
def test_versioned_config_rejects_unknown_or_invalid_screening(
    api_context: ApiContext,
    screening: dict[str, object],
) -> None:
    response = api_context.client.post(
        "/job-search/configs",
        headers={"X-Rufina-Owner-Id": "invalid-screening-owner"},
        json={
            "name": "Invalid screening",
            "filters": {
                "schemaVersion": 2,
                "search": {"keywords": "Python"},
                "screening": screening,
            },
        },
    )

    assert response.status_code == 422


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
    assert first.json()["jobsAlreadyKnown"] == 2
    assert first.json()["jobsAdded"] == 1
    assert first.json()["jobsAnalyzed"] == 1
    assert [job["title"] for job in matched_batches[0]] == ["New Engineer"]
    assert second.status_code == 200
    assert second.json()["jobsAlreadyKnown"] == 3
    assert second.json()["jobsAdded"] == 0
    assert second.json()["jobsAnalyzed"] == 0
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


def screening_filters() -> dict[str, object]:
    return {
        "schemaVersion": 2,
        "search": {
            "keywords": "Software Engineer",
            "location": "Zurich",
        },
        "screening": {
            "enabled": True,
            "targetRoles": ["Software Engineer"],
            "allowedSeniority": [],
            "excludedSeniority": [],
            "hardRules": [],
        },
    }


def grant_ai_consent(context: ApiContext, *, owner_id: str) -> None:
    now = datetime.now(UTC)
    with context.sessions() as db:
        db.add(
            AiPrivacySettingsRecord(
                owner_id=owner_id,
                consent_version=context.settings.ai_consent_version,
                consent_backend=context.settings.ai_backend_mode,
                consented_at=now,
                retention_days=30,
                updated_at=now,
            )
        )
        db.commit()


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
