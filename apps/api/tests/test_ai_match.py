import json
import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.settings import Settings, get_settings
from app.main import app
from app.models.profile import ProfilePayload, ProfileRecord
from app.services.ai_match import calculate_ai_matches, parse_number


def test_parse_number_reads_spaced_salary_values() -> None:
    assert parse_number("CHF 100 000") == 100000
    assert parse_number("$120k - $160k") == 160000


def test_local_ai_match_scores_relevant_job_higher() -> None:
    profile = ProfilePayload(
        current_role="Machine Learning Engineer",
        desired_role="Audio ML Engineer",
        location="Zurich",
        skills="Python\nPyTorch\nMachine Learning\nAudio Processing\nComputer Vision",
        job_preferences=json.dumps(
            {
                "desired_roles": ["Machine Learning Engineer"],
                "locations": ["Zurich"],
                "work_formats": ["Hybrid", "Remote"],
                "employment_types": ["Full-Time"],
                "salary_min": "100000",
                "salary_currency": "CHF",
            }
        ),
        resume_file_name="resume.pdf",
        resume_data_url="data:application/pdf;base64,JVBERi0x",
    )
    relevant_job = {
        "id": "linkedin-audio-ml",
        "title": "Audio Machine Learning Engineer",
        "company": "Google",
        "location": "Zurich",
        "type": "Full-Time",
        "salary": "Not specified",
        "posted": "LinkedIn",
        "experience": "Mid-Senior level",
        "department": "Research",
        "match": 50,
        "logo": "linkedin",
        "overview": "Build PyTorch models for audio face tracking and computer vision.",
        "responsibilities": ["Train machine learning models"],
        "requirements": ["Python", "PyTorch", "Machine Learning"],
        "skills": ["Python", "PyTorch", "Machine Learning"],
    }
    unrelated_job = {
        **relevant_job,
        "id": "linkedin-accounting",
        "title": "Accounting Manager",
        "overview": "Own accounting close and financial reporting.",
        "requirements": ["CPA", "IFRS"],
        "skills": ["Accounting", "IFRS"],
    }

    matched = calculate_ai_matches(
        profile,
        [relevant_job, unrelated_job],
        command="openclaw",
        agent_id="main",
        thinking="low",
        timeout_seconds=1,
        openclaw_enabled=False,
        openclaw_max_jobs=0,
    )

    assert matched[0]["match"] > matched[1]["match"]
    assert matched[0]["aiMatch"]["source"] == "local"
    assert matched[0]["aiMatch"]["reasons"]


def test_ai_match_endpoint_updates_and_persists_job_scores() -> None:
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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=False)
    client = TestClient(app)

    try:
        with testing_session_local() as db:
            db.add(
                ProfileRecord(
                    id="default",
                    data=ProfilePayload(
                        current_role="Machine Learning Engineer",
                        desired_role="ML Software Engineer",
                        location="Zurich",
                        skills="Python\nMachine Learning\nPyTorch",
                        job_preferences=json.dumps({"locations": ["Zurich"], "work_formats": ["Hybrid"]}),
                    ).model_dump(),
                )
            )
            db.commit()

        job = {
            "id": "linkedin-ml-engineer",
            "company": "Google",
            "title": "XR Audio Face Tracking ML Software Engineer",
            "location": "Zurich",
            "type": "Full-Time",
            "salary": "Not specified",
            "posted": "LinkedIn",
            "experience": "Mid-Senior level",
            "department": "LinkedIn import",
            "match": 50,
            "logo": "linkedin",
            "overview": "Work on machine learning systems using Python and PyTorch.",
            "responsibilities": ["Build ML systems"],
            "requirements": ["Python", "Machine Learning"],
            "skills": ["Python", "Machine Learning"],
        }

        response = client.post("/jobs/ai-match", json={"jobs": [{"id": job["id"], "data": job}]})
        read_response = client.get("/jobs")

        assert response.status_code == 200
        payload = response.json()[0]["data"]
        assert payload["match"] != 50
        assert payload["aiMatch"]["source"] == "local"
        assert payload["aiMatch"]["cacheKey"]
        assert read_response.json()[0]["data"]["aiMatch"]["score"] == payload["match"]
    finally:
        app.dependency_overrides.clear()


def test_ai_match_endpoint_force_reruns_only_recent_jobs() -> None:
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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=False)
    client = TestClient(app)

    try:
        with testing_session_local() as db:
            db.add(
                ProfileRecord(
                    id="default",
                    data=ProfilePayload(
                        current_role="Machine Learning Engineer",
                        desired_role="ML Software Engineer",
                        location="Zurich",
                        skills="Python\nMachine Learning\nPyTorch",
                        job_preferences=json.dumps({"locations": ["Zurich"], "work_formats": ["Hybrid"]}),
                    ).model_dump(),
                )
            )
            db.commit()

        def build_job(job_id: str, added_at: str) -> dict[str, object]:
            return {
                "id": job_id,
                "company": "Google",
                "title": "XR Audio Face Tracking ML Software Engineer",
                "location": "Zurich",
                "type": "Full-Time",
                "salary": "Not specified",
                "posted": "LinkedIn",
                "experience": "Mid-Senior level",
                "department": "LinkedIn import",
                "match": 50,
                "logo": "linkedin",
                "overview": "Work on machine learning systems using Python and PyTorch.",
                "responsibilities": ["Build ML systems"],
                "requirements": ["Python", "Machine Learning"],
                "skills": ["Python", "Machine Learning"],
                "addedAt": added_at,
            }

        now = datetime.now(UTC)
        recent_job = build_job("linkedin-recent-force-ml-engineer", now.isoformat())
        old_job = build_job("linkedin-old-force-ml-engineer", (now - timedelta(days=3)).isoformat())

        first_response = client.post(
            "/jobs/ai-match",
            json={
                "jobs": [
                    {"id": recent_job["id"], "data": recent_job},
                    {"id": old_job["id"], "data": old_job},
                ]
            },
        )
        assert first_response.status_code == 200
        cached_jobs = {job["id"]: job["data"] for job in first_response.json()}
        time.sleep(0.01)

        force_response = client.post(
            "/jobs/ai-match?force=true",
            json={
                "jobs": [
                    {"id": recent_job["id"], "data": cached_jobs[recent_job["id"]]},
                    {"id": old_job["id"], "data": cached_jobs[old_job["id"]]},
                ]
            },
        )

        assert force_response.status_code == 200
        forced_jobs = {job["id"]: job["data"] for job in force_response.json()}
        assert (
            forced_jobs[recent_job["id"]]["aiMatch"]["updatedAt"]
            != cached_jobs[recent_job["id"]]["aiMatch"]["updatedAt"]
        )
        assert (
            forced_jobs[old_job["id"]]["aiMatch"]["updatedAt"]
            == cached_jobs[old_job["id"]]["aiMatch"]["updatedAt"]
        )
    finally:
        app.dependency_overrides.clear()


def test_ai_match_run_endpoint_updates_status_and_persists_job_scores() -> None:
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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=False)
    client = TestClient(app)

    try:
        with testing_session_local() as db:
            db.add(
                ProfileRecord(
                    id="default",
                    data=ProfilePayload(
                        current_role="Machine Learning Engineer",
                        desired_role="ML Software Engineer",
                        location="Zurich",
                        skills="Python\nMachine Learning\nPyTorch",
                        job_preferences=json.dumps({"locations": ["Zurich"], "work_formats": ["Hybrid"]}),
                    ).model_dump(),
                )
            )
            db.commit()

        job = {
            "id": "linkedin-async-ml-engineer",
            "company": "Google",
            "title": "XR Audio Face Tracking ML Software Engineer",
            "location": "Zurich",
            "type": "Full-Time",
            "salary": "Not specified",
            "posted": "LinkedIn",
            "experience": "Mid-Senior level",
            "department": "LinkedIn import",
            "match": 50,
            "logo": "linkedin",
            "overview": "Work on machine learning systems using Python and PyTorch.",
            "responsibilities": ["Build ML systems"],
            "requirements": ["Python", "Machine Learning"],
            "skills": ["Python", "Machine Learning"],
        }

        run_response = client.post(
            "/jobs/ai-match/run",
            json={"jobs": [{"id": job["id"], "data": job}]},
        )

        assert run_response.status_code == 202
        assert run_response.json()["status"] in {"queued", "running"}

        status_payload = {}
        for _ in range(20):
            status_response = client.get("/jobs/ai-match/status")
            assert status_response.status_code == 200
            status_payload = status_response.json()
            if status_payload["status"] == "completed":
                break
            time.sleep(0.05)

        assert status_payload["status"] == "completed"
        assert status_payload["processed"] == status_payload["total"] == 1
        payload = status_payload["updatedJobs"][0]["data"]
        assert payload["match"] != 50
        assert payload["aiMatch"]["source"] == "local"

        read_response = client.get("/jobs")
        assert read_response.json()[0]["data"]["aiMatch"]["score"] == payload["match"]
    finally:
        app.dependency_overrides.clear()
