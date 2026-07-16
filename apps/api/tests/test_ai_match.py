import json
import time
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.settings import Settings, get_settings
from app.main import app
from app.models.jobs import JobMatchFeedbackRecord, JobMatchRecord, StoredJobRecord
from app.models.profile import CandidateMatchSnapshotRecord, ProfilePayload, ProfileRecord
from app.services import ai_match as ai_match_service
from app.services.ai_match import (
    OpenClawAiMatchError,
    build_job_snapshot,
    build_openclaw_ai_match_prompt,
    calculate_ai_matches,
    extract_openclaw_ai_match_payload,
    infer_seniority,
    parse_number,
)
from app.services.candidate_snapshot import (
    CandidateSnapshotError,
    build_profile_input_hash,
    extract_openclaw_candidate_snapshot_payload,
)


def install_openclaw_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_build_snapshot_with_openclaw(*, fallback_snapshot: dict, **_: object) -> dict:
        return fallback_snapshot

    def fake_score_with_openclaw(*, jobs: list[dict], **_: object) -> list[dict]:
        matches = []
        for job in jobs:
            title = str(job.get("title") or "")
            is_relevant = "Accounting" not in title
            matches.append(
                {
                    "id": job["id"],
                    "score": 88 if is_relevant else 34,
                    "confidence": "high" if is_relevant else "medium",
                    "breakdown": {
                        "role_fit": 18 if is_relevant else 3,
                        "skills_fit": 26 if is_relevant else 2,
                        "experience_fit": 14 if is_relevant else 5,
                        "preferences_fit": 14 if is_relevant else 6,
                        "constraints_fit": 10,
                        "industry_fit": 4 if is_relevant else 1,
                        "evidence_fit": 2,
                    },
                    "reasons": ["OpenClaw matched this role"] if is_relevant else ["OpenClaw found weak overlap"],
                    "gaps": ["No major gaps detected from available data"] if is_relevant else ["Role is not aligned"],
                    "applicationGuide": {
                        "language": "English",
                        "positioning": "Lead with verified machine learning experience.",
                        "readiness": "needs_confirmation",
                        "roleMission": "Build reliable machine learning systems for the product.",
                        "hiringPriorities": ["Ship production-ready ML features."],
                        "mustHave": ["Python", "Machine Learning"],
                        "niceToHave": ["PyTorch"],
                        "hardConstraints": [],
                        "evidenceMatrix": [
                            {
                                "requirement": "Python",
                                "importance": "required",
                                "status": "verified",
                                "evidence": "Python is listed in the candidate profile.",
                                "action": "Lead with the strongest Python project.",
                            }
                        ],
                        "clarificationQuestions": [
                            {
                                "id": "production-ml",
                                "requirement": "Production ML",
                                "question": "Which ML model did you deploy to production?",
                                "why": "This is a core responsibility.",
                                "claimIfConfirmed": "Deployed an ML model to production.",
                                "blocking": True,
                            }
                        ],
                        "resumePlan": {
                            "targetHeadline": "Machine Learning Engineer",
                            "summaryFocus": "Verified ML delivery experience.",
                            "evidenceToLead": ["Python project evidence"],
                            "bulletStrategy": ["Lead with the strongest verified ML result."],
                        },
                        "coverLetterPlan": {
                            "openingAngle": "Connect verified ML work to the product mission.",
                            "proofPoints": ["Python project evidence"],
                            "motivationAngle": "Focus on the role's technical mission.",
                        },
                        "cvImprovements": ["Move relevant Python evidence into the summary."],
                        "coverLetterStrategy": ["Connect verified project evidence to the role."],
                        "risks": ["Do not claim tools absent from the profile."],
                        "keywords": ["Python", "Machine Learning"],
                        "applicationQuestions": ["Describe a relevant ML project using verified facts."],
                        "finalChecklist": ["Verify every claim against the source CV."],
                    },
                }
            )
        return matches

    monkeypatch.setattr("app.services.candidate_snapshot.build_snapshot_with_openclaw", fake_build_snapshot_with_openclaw)
    monkeypatch.setattr(ai_match_service, "score_with_openclaw", fake_score_with_openclaw)


def test_parse_number_reads_spaced_salary_values() -> None:
    assert parse_number("CHF 100 000") == 100000
    assert parse_number("$120k - $160k") == 160000


def test_openclaw_ai_match_scores_relevant_job_higher(monkeypatch: pytest.MonkeyPatch) -> None:
    install_openclaw_fakes(monkeypatch)
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
        openclaw_enabled=True,
        openclaw_max_jobs=20,
    )

    assert matched[0]["match"] > matched[1]["match"]
    assert matched[0]["aiMatch"]["source"] == "openclaw"
    assert matched[0]["aiMatch"]["reasons"]


def test_ai_match_requires_openclaw_enabled() -> None:
    profile = ProfilePayload(
        current_role="Senior LLM Engineer",
        desired_role="GenAI Platform Engineer",
        location="Zurich",
        skills="LLM\nMLOps\nReact.js\nNode",
        job_preferences=json.dumps(
            {
                "desired_roles": ["Generative AI Engineer"],
                "locations": ["Zurich"],
                "work_formats": ["Remote"],
                "employment_types": ["Full-Time"],
                "salary_min": "130000",
                "salary_currency": "CHF",
                "seniority": ["Senior"],
            }
        ),
    )
    job = {
        "id": "linkedin-genai-platform",
        "title": "Sr. GenAI Platform Engineer",
        "company": "Open Systems",
        "location": "Zürich, Switzerland / Remote EU",
        "type": "Full-Time Remote",
        "salary": "€140k - €160k",
        "posted": "LinkedIn",
        "experience": "Experienced",
        "department": "AI Platform",
        "match": 50,
        "logo": "linkedin",
        "overview": "Build LLM products with React, Node.js, and production ML Ops workflows.",
        "responsibilities": ["Ship large language model features"],
        "requirements": ["Generative AI", "React", "Node.js", "Machine Learning Operations"],
        "skills": ["GenAI", "React", "Node.js", "MLOps"],
    }

    with pytest.raises(OpenClawAiMatchError, match="required but disabled"):
        calculate_ai_matches(
            profile,
            [job],
            command="openclaw",
            agent_id="main",
            thinking="low",
            timeout_seconds=1,
            openclaw_enabled=False,
            openclaw_max_jobs=0,
        )


def test_openclaw_prompt_treats_score_as_expert_judgment() -> None:
    profile_snapshot = {
        "roles": ["Machine Learning Engineer"],
        "skills": ["Python", "PyTorch"],
    }
    job_snapshot = build_job_snapshot(
        {
            "id": "linkedin-prompt-ml-engineer",
            "title": "Machine Learning Engineer",
            "company": "Google",
            "location": "Zurich",
            "type": "Full-Time",
            "salary": "Not specified",
            "posted": "LinkedIn",
            "experience": "Mid-Senior level",
            "department": "LinkedIn import",
            "overview": "Work on machine learning systems using Python and PyTorch.",
            "responsibilities": ["Build ML systems"],
            "requirements": ["Python", "Machine Learning"],
            "skills": ["Python", "Machine Learning"],
        }
    )

    prompt = build_openclaw_ai_match_prompt(profile_snapshot, [job_snapshot])

    assert "score as your expert judgment from 0 to 100" in prompt
    assert "not an arithmetic sum of breakdown values" in prompt
    assert "breakdownMaxScores" in prompt
    assert '"applicationGuide"' in prompt
    assert '"language":"English|German"' in prompt
    assert '"evidenceMatrix"' in prompt
    assert '"clarificationQuestions"' in prompt
    assert "if a data role requires Excel" in prompt
    assert "reuse directly when tailoring the candidate's CV and cover letter" in prompt
    assert '"weights"' not in prompt


def test_openclaw_candidate_snapshot_reads_top_level_payloads_text() -> None:
    payload = extract_openclaw_candidate_snapshot_payload(
        json.dumps(
            {
                "payloads": [
                    {
                        "text": json.dumps(
                            {
                                "candidate": {
                                    "roles": ["Backend Developer"],
                                    "skills": ["Python", "FastAPI"],
                                }
                            }
                        )
                    }
                ]
            }
        )
    )

    assert payload["roles"] == ["Backend Developer"]
    assert payload["skills"] == ["Python", "FastAPI"]


def test_openclaw_ai_match_reads_top_level_payloads_text() -> None:
    payload = extract_openclaw_ai_match_payload(
        json.dumps(
            {
                "payloads": [
                    {
                        "text": json.dumps(
                            {
                                "matches": [
                                    {
                                        "id": "linkedin-python-backend",
                                        "score": 83,
                                        "breakdown": {
                                            "role_fit": 16,
                                            "skills_fit": 25,
                                            "experience_fit": 13,
                                            "preferences_fit": 12,
                                            "constraints_fit": 8,
                                            "industry_fit": 4,
                                            "evidence_fit": 3,
                                        },
                                    }
                                ]
                            }
                        )
                    }
                ]
            }
        )
    )

    assert payload["matches"][0]["id"] == "linkedin-python-backend"
    assert payload["matches"][0]["score"] == 83


def test_seniority_normalization_handles_common_variants() -> None:
    assert infer_seniority("Sr. Machine Learning Engineer") == "senior"
    assert infer_seniority("Mid-Senior level software engineer") == "senior"
    assert infer_seniority("Principal AI Architect") == "lead"
    assert infer_seniority("Entry level graduate developer") == "junior"


def test_ai_match_endpoint_requires_openclaw_candidate_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_build_snapshot_with_openclaw(**_: object) -> dict:
        raise CandidateSnapshotError("snapshot failed")

    def fail_score_with_openclaw(**_: object) -> list[dict]:
        raise AssertionError("job scoring should not run without an OpenClaw candidate snapshot")

    monkeypatch.setattr(
        "app.services.candidate_snapshot.build_snapshot_with_openclaw",
        fail_build_snapshot_with_openclaw,
    )
    monkeypatch.setattr(ai_match_service, "score_with_openclaw", fail_score_with_openclaw)

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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=True)
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
                    ).model_dump(),
                )
            )
            db.commit()

        job = {
            "id": "linkedin-strict-snapshot",
            "company": "Google",
            "title": "Machine Learning Engineer",
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

        assert response.status_code == 502
        assert response.json()["detail"] == "snapshot failed"
        with testing_session_local() as db:
            assert db.query(CandidateMatchSnapshotRecord).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_ai_match_endpoint_ignores_cached_local_candidate_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_calls = 0
    fallback_roles_seen: list[list[str]] = []

    def fake_build_snapshot_with_openclaw(*, fallback_snapshot: dict, **_: object) -> dict:
        nonlocal snapshot_calls
        snapshot_calls += 1
        fallback_roles_seen.append(fallback_snapshot.get("roles", []))
        return {**fallback_snapshot, "roles": ["openclaw normalized role"]}

    monkeypatch.setattr(
        "app.services.candidate_snapshot.build_snapshot_with_openclaw",
        fake_build_snapshot_with_openclaw,
    )

    def fake_score_with_openclaw(*, jobs: list[dict], **_: object) -> list[dict]:
        return [
            {
                "id": job["id"],
                "score": 87,
                "confidence": "high",
                "breakdown": {
                    "role_fit": 18,
                    "skills_fit": 25,
                    "experience_fit": 14,
                    "preferences_fit": 14,
                    "constraints_fit": 10,
                    "industry_fit": 4,
                    "evidence_fit": 2,
                },
                "reasons": ["OpenClaw matched this role"],
                "gaps": ["No major gaps detected from available data"],
            }
            for job in jobs
        ]

    monkeypatch.setattr(ai_match_service, "score_with_openclaw", fake_score_with_openclaw)

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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=True)
    client = TestClient(app)

    try:
        profile = ProfilePayload(
            current_role="Machine Learning Engineer",
            desired_role="ML Software Engineer",
            location="Zurich",
            skills="Python\nMachine Learning\nPyTorch",
        )
        with testing_session_local() as db:
            db.add(ProfileRecord(id="default", data=profile.model_dump()))
            db.add(
                CandidateMatchSnapshotRecord(
                    id="cached-local-snapshot",
                    profile_input_hash=build_profile_input_hash(profile),
                    profile_hash="cached-local-profile-hash",
                    matcher_version="ai-match-v1",
                    source="local",
                    data={"roles": ["cached local role"], "skills": []},
                    openclaw_error="previous fallback",
                    created_at=datetime.now(UTC),
                )
            )
            db.commit()

        job = {
            "id": "linkedin-ignore-local-snapshot",
            "company": "Google",
            "title": "Machine Learning Engineer",
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

        assert response.status_code == 200
        assert snapshot_calls == 1
        assert fallback_roles_seen == [[]]
        with testing_session_local() as db:
            snapshot_sources = [
                record.source
                for record in db.query(CandidateMatchSnapshotRecord).all()
            ]
            assert snapshot_sources.count("local") == 1
            assert snapshot_sources.count("openclaw") == 1
    finally:
        app.dependency_overrides.clear()


def test_ai_match_endpoint_rejects_incomplete_openclaw_breakdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_build_snapshot_with_openclaw(*, fallback_snapshot: dict, **_: object) -> dict:
        return {**fallback_snapshot, "roles": ["openclaw normalized role"]}

    def fake_score_with_openclaw(*, jobs: list[dict], **_: object) -> list[dict]:
        return [
            {
                "id": jobs[0]["id"],
                "score": 81,
                "confidence": "high",
                "breakdown": {
                    "role_fit": 18,
                    "skills_fit": 24,
                },
                "reasons": ["OpenClaw matched this role"],
                "gaps": ["No major gaps detected from available data"],
            }
        ]

    monkeypatch.setattr(
        "app.services.candidate_snapshot.build_snapshot_with_openclaw",
        fake_build_snapshot_with_openclaw,
    )
    monkeypatch.setattr(ai_match_service, "score_with_openclaw", fake_score_with_openclaw)

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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=True)
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
                    ).model_dump(),
                )
            )
            db.commit()

        job = {
            "id": "linkedin-incomplete-openclaw-breakdown",
            "company": "Google",
            "title": "Machine Learning Engineer",
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

        assert response.status_code == 502
        assert "missing breakdown keys" in response.json()["detail"]
        assert "experience_fit" in response.json()["detail"]
        with testing_session_local() as db:
            assert db.query(JobMatchRecord).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_ai_match_endpoint_updates_and_persists_job_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    install_openclaw_fakes(monkeypatch)
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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=True)
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
        assert payload["aiMatch"]["source"] == "openclaw"
        assert payload["aiMatch"]["cacheKey"]
        assert payload["aiMatch"]["applicationGuide"]["language"] == "English"
        assert payload["aiMatch"]["applicationGuide"]["cvImprovements"]
        assert payload["aiMatch"]["applicationGuide"]["roleMission"]
        assert payload["aiMatch"]["applicationGuide"]["evidenceMatrix"][0]["status"] == "verified"
        assert payload["aiMatch"]["applicationGuide"]["clarificationQuestions"][0]["blocking"] is True
        assert read_response.json()[0]["data"]["aiMatch"]["score"] == payload["match"]
        assert (
            read_response.json()[0]["data"]["aiMatch"]["applicationGuide"]
            == payload["aiMatch"]["applicationGuide"]
        )

        feedback_response = client.post(
            f"/jobs/{job['id']}/match-feedback",
            json={"feedback": "bad_match"},
        )
        assert feedback_response.status_code == 200
        feedback_payload = feedback_response.json()["data"]
        assert feedback_payload["aiMatch"]["feedback"] == "bad_match"

        rerun_response = client.post(
            "/jobs/ai-match?force=true",
            json={"jobs": [{"id": job["id"], "data": feedback_payload}]},
        )
        assert rerun_response.status_code == 200
        rerun_payload = rerun_response.json()[0]["data"]
        assert rerun_payload["match"] < feedback_payload["match"]
        assert rerun_payload["aiMatch"]["calibration"]["feedback"] == "bad_match"

        with testing_session_local() as db:
            stored_job = db.get(StoredJobRecord, job["id"])
            match_records = db.query(JobMatchRecord).filter(JobMatchRecord.job_id == job["id"]).all()
            feedback_records = db.query(JobMatchFeedbackRecord).filter(JobMatchFeedbackRecord.job_id == job["id"]).all()
            snapshot_records = db.query(CandidateMatchSnapshotRecord).all()
            assert stored_job is not None
            assert "aiMatch" not in stored_job.data
            assert len(snapshot_records) == 1
            assert snapshot_records[0].source == "openclaw"
            assert len(match_records) == 2
            assert len(feedback_records) == 1
            assert {record.profile_hash for record in match_records} == {snapshot_records[0].profile_hash}
            assert rerun_payload["match"] in {record.score for record in match_records}
            assert all(record.source == "openclaw" for record in match_records)
            assert all(record.breakdown for record in match_records)
            assert all("_applicationGuide" in record.breakdown for record in match_records)
    finally:
        app.dependency_overrides.clear()


def test_ai_match_endpoint_force_reruns_cached_openclaw_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    install_openclaw_fakes(monkeypatch)
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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=True)
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
            != cached_jobs[old_job["id"]]["aiMatch"]["updatedAt"]
        )
    finally:
        app.dependency_overrides.clear()


def test_ai_match_run_endpoint_updates_status_and_persists_job_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    install_openclaw_fakes(monkeypatch)
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
    app.dependency_overrides[get_settings] = lambda: Settings(openclaw_ai_match_enabled=True)
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
        # The background worker may finish before TestClient returns when the scorer is mocked.
        assert run_response.json()["status"] in {"queued", "running", "completed"}

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
        assert payload["aiMatch"]["source"] == "openclaw"

        read_response = client.get("/jobs")
        assert read_response.json()[0]["data"]["aiMatch"]["score"] == payload["match"]
    finally:
        app.dependency_overrides.clear()


def test_ai_match_run_endpoint_batches_openclaw_scoring(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_build_snapshot_with_openclaw(*, fallback_snapshot: dict, **_: object) -> dict:
        return {**fallback_snapshot, "roles": ["openclaw normalized role"]}

    batch_sizes: list[int] = []

    def fake_score_with_openclaw(*, jobs: list[dict], **_: object) -> list[dict]:
        batch_sizes.append(len(jobs))
        return [
            {
                "id": job["id"],
                "score": 82,
                "confidence": "high",
                "breakdown": {
                    "role_fit": 17,
                    "skills_fit": 24,
                    "experience_fit": 13,
                    "preferences_fit": 13,
                    "constraints_fit": 10,
                    "industry_fit": 3,
                    "evidence_fit": 2,
                },
                "reasons": ["OpenClaw matched this role"],
                "gaps": ["No major gaps detected from available data"],
            }
            for job in jobs
        ]

    monkeypatch.setattr(
        "app.services.candidate_snapshot.build_snapshot_with_openclaw",
        fake_build_snapshot_with_openclaw,
    )
    monkeypatch.setattr(ai_match_service, "score_with_openclaw", fake_score_with_openclaw)

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
    app.dependency_overrides[get_settings] = lambda: Settings(
        openclaw_ai_match_enabled=True,
        openclaw_ai_match_max_jobs=2,
    )
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
                    ).model_dump(),
                )
            )
            db.commit()

        def build_job(index: int) -> dict[str, object]:
            return {
                "id": f"linkedin-async-batch-ml-engineer-{index}",
                "company": "Google",
                "title": f"Machine Learning Engineer {index}",
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

        jobs = [build_job(index) for index in range(5)]
        run_response = client.post(
            "/jobs/ai-match/run",
            json={"jobs": [{"id": job["id"], "data": job} for job in jobs]},
        )

        assert run_response.status_code == 202

        status_payload = {}
        for _ in range(20):
            status_response = client.get("/jobs/ai-match/status")
            assert status_response.status_code == 200
            status_payload = status_response.json()
            if status_payload["status"] == "completed":
                break
            time.sleep(0.05)

        assert status_payload["status"] == "completed"
        assert status_payload["processed"] == status_payload["total"] == 5
        assert len(status_payload["updatedJobs"]) == 5
        assert batch_sizes == [2, 2, 1]
    finally:
        app.dependency_overrides.clear()
