from collections.abc import Generator
import base64
from datetime import UTC, datetime
from io import BytesIO
import json

import pytest
from docx import Document
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import documents as documents_api
from app.core.database import Base, get_db
from app.main import app
from app.models.applications import StoredApplicationRecord
from app.models.documents import (
    DocumentPackJobRecord,
    DocumentRecord,
    DocumentVersionRecord,
)
from app.models.jobs import JobMatchRecord, StoredJobRecord
from app.models.profile import ProfileRecord
from app.services.ai_match import MATCHER_VERSION
from app.services.document_validation import DocumentValidationError
from app.services.job_match_store import APPLICATION_GUIDE_STORAGE_KEY


@pytest.fixture
def pack_client() -> Generator[tuple[TestClient, sessionmaker[Session]], None, None]:
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

    with testing_session_local() as db:
        db.add_all(
            [
                StoredApplicationRecord(
                    id="application-pack",
                    data={
                        "id": "application-pack",
                        "status": "draft",
                        "job": {"id": "vacancy-1"},
                    },
                ),
                StoredJobRecord(
                    id="vacancy-1",
                    data={
                        "id": "vacancy-1",
                        "title": "Backend Engineer",
                        "company": "Acme",
                        "overview": "Build Python services.",
                    },
                ),
                ProfileRecord(
                    id="default",
                    data={
                        "name": "Alex",
                        "experience": "Python delivery at Acme in 2023",
                        "skills": "Python",
                    },
                ),
                JobMatchRecord(
                    id="match-pack",
                    job_id="vacancy-1",
                    profile_hash="profile-pack",
                    matcher_version=MATCHER_VERSION,
                    cache_key="cache-pack",
                    score=90,
                    source="openclaw",
                    confidence="high",
                    breakdown={
                        APPLICATION_GUIDE_STORAGE_KEY: {
                            "language": "English",
                            "clarificationQuestions": [],
                            "evidenceMatrix": [
                                {
                                    "requirement": "Python delivery",
                                    "status": "verified",
                                    "evidence": "Python delivery at Acme in 2023",
                                }
                            ],
                        }
                    },
                    reasons=[],
                    gaps=[],
                    heuristic_score=90,
                    created_at=datetime.now(UTC),
                ),
            ]
        )
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), testing_session_local
    finally:
        app.dependency_overrides.clear()


def document_data_url(document: Document) -> str:
    output = BytesIO()
    document.save(output)
    return (
        "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;"
        "base64," + base64.b64encode(output.getvalue()).decode()
    )


def upload_pack_templates(client: TestClient) -> tuple[str, str]:
    resume = Document()
    resume.add_paragraph("Original resume summary.")
    cover = Document()
    cover.add_paragraph("Dear Hiring Team,")
    cover.add_paragraph("Original cover letter body.")
    cover.add_paragraph("Kind regards,")
    resume_response = client.post(
        "/documents/templates",
        json={
            "type": "tailored_resume",
            "name": "Pack CV",
            "fileName": "cv.docx",
            "dataUrl": document_data_url(resume),
        },
    )
    cover_response = client.post(
        "/documents/templates",
        json={
            "type": "cover_letter",
            "name": "Pack cover letter",
            "fileName": "cover.docx",
            "dataUrl": document_data_url(cover),
        },
    )
    assert resume_response.status_code == 201
    assert cover_response.status_code == 201
    return resume_response.json()["id"], cover_response.json()["id"]


def pack_request(
    resume_template_id: str,
    cover_template_id: str,
    *,
    persistence_mode: str = "atomic",
    include_cover: bool = True,
) -> dict[str, object]:
    resume = {
        "title": "Tailored CV",
        "content": json.dumps({"replacements": []}),
        "templateId": resume_template_id,
        "generationFingerprint": "a" * 64,
        "generationModel": "test-model",
        "inputVersions": {"profile": "profile-v1"},
    }
    cover = {
        "title": "Cover letter",
        "content": "Dear Hiring Team,\n\nPython delivery at Acme in 2023.\n\nKind regards,",
        "templateId": cover_template_id,
        "generationFingerprint": "b" * 64,
        "generationModel": "test-model",
        "inputVersions": {"profile": "profile-v1"},
    }
    return {
        "packJobId": "pack-job-1",
        "jobId": "vacancy-1",
        "applicationId": "application-pack",
        "persistenceMode": persistence_mode,
        "resume": resume,
        "coverLetter": cover if include_cover else None,
        "partialReason": None if include_cover else "Cover generation exhausted retries",
    }


def validation_report(document_type: str) -> dict[str, object]:
    return {
        "factual": {"status": "passed", "checkedChanges": 0},
        "visual": {
            "status": "passed",
            "sourcePageCount": 1,
            "renderedPageCount": 1,
            "linksPreserved": True,
            "tableOverflow": False,
        },
        "diff": [],
        "documentType": document_type,
    }


def test_atomic_pack_commits_both_documents_and_retry_is_idempotent(
    pack_client,
    monkeypatch,
) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)
    calls: list[str] = []

    def validate(**kwargs):
        calls.append(kwargs["document_type"])
        return validation_report(kwargs["document_type"])

    monkeypatch.setattr("app.api.documents.validate_generated_document", validate)
    request = pack_request(resume_template_id, cover_template_id)

    created = client.post("/documents/packs", json=request)
    retried = client.post("/documents/packs", json=request)

    with testing_session_local() as db:
        document_count = db.scalar(select(func.count()).select_from(DocumentRecord))
        version_count = db.scalar(select(func.count()).select_from(DocumentVersionRecord))
        job_count = db.scalar(select(func.count()).select_from(DocumentPackJobRecord))

    assert created.status_code == 201
    assert created.json()["status"] == "completed"
    assert len(created.json()["documents"]) == 2
    assert [stage["status"] for stage in created.json()["stages"]] == [
        "completed",
        "completed",
        "completed",
    ]
    assert retried.status_code == 201
    assert retried.json()["documents"] == created.json()["documents"]
    assert calls == ["tailored_resume", "cover_letter"]
    assert document_count == 2
    assert version_count == 2
    assert job_count == 1


def test_resume_preflight_validates_without_saving(pack_client, monkeypatch) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)
    monkeypatch.setattr(
        "app.api.documents.validate_generated_document",
        lambda **kwargs: validation_report(kwargs["document_type"]),
    )
    request = pack_request(resume_template_id, cover_template_id)

    response = client.post(
        "/documents/packs/validate-resume",
        json={
            "applicationId": request["applicationId"],
            "resume": request["resume"],
        },
    )

    with testing_session_local() as db:
        document_count = db.scalar(select(func.count()).select_from(DocumentRecord))
        job_count = db.scalar(select(func.count()).select_from(DocumentPackJobRecord))

    assert response.status_code == 200
    assert response.json()["status"] == "passed"
    assert response.json()["validation"]["documentType"] == "tailored_resume"
    assert document_count == 0
    assert job_count == 0


def test_atomic_pack_updates_both_documents_as_one_idempotent_version_batch(
    pack_client,
    monkeypatch,
) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)
    monkeypatch.setattr(
        "app.api.documents.validate_generated_document",
        lambda **kwargs: validation_report(kwargs["document_type"]),
    )
    initial_request = pack_request(resume_template_id, cover_template_id)
    initial = client.post("/documents/packs", json=initial_request)
    documents_by_type = {
        document["type"]: document for document in initial.json()["documents"]
    }
    update_request = pack_request(resume_template_id, cover_template_id)
    update_request["packJobId"] = "pack-job-2"
    update_request["resume"]["documentId"] = documents_by_type["tailored_resume"]["id"]
    update_request["coverLetter"]["documentId"] = documents_by_type["cover_letter"]["id"]

    updated = client.post("/documents/packs", json=update_request)
    retried = client.post("/documents/packs", json=update_request)

    with testing_session_local() as db:
        version_count = db.scalar(select(func.count()).select_from(DocumentVersionRecord))

    assert initial.status_code == 201
    assert updated.status_code == 201
    assert {document["currentVersion"] for document in updated.json()["documents"]} == {2}
    assert retried.json()["documents"] == updated.json()["documents"]
    assert version_count == 4


def test_atomic_pack_stops_after_failed_cv_validation(pack_client, monkeypatch) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)
    calls: list[str] = []

    def validate(**kwargs):
        calls.append(kwargs["document_type"])
        raise DocumentValidationError("CV contains an unsupported claim")

    monkeypatch.setattr("app.api.documents.validate_generated_document", validate)

    response = client.post(
        "/documents/packs",
        json=pack_request(resume_template_id, cover_template_id),
    )

    with testing_session_local() as db:
        document_count = db.scalar(select(func.count()).select_from(DocumentRecord))
        job_count = db.scalar(select(func.count()).select_from(DocumentPackJobRecord))

    assert response.status_code == 422
    assert response.json()["detail"]["stage"] == "resume_validation"
    assert response.json()["detail"]["status"] == "rolled_back"
    assert calls == ["tailored_resume"]
    assert document_count == 0
    assert job_count == 0


def test_atomic_pack_rolls_back_when_cover_letter_validation_fails(
    pack_client,
    monkeypatch,
) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)

    def validate(**kwargs):
        if kwargs["document_type"] == "cover_letter":
            raise DocumentValidationError("Cover letter adds an unsupported company")
        return validation_report(kwargs["document_type"])

    monkeypatch.setattr("app.api.documents.validate_generated_document", validate)

    response = client.post(
        "/documents/packs",
        json=pack_request(resume_template_id, cover_template_id),
    )

    with testing_session_local() as db:
        document_count = db.scalar(select(func.count()).select_from(DocumentRecord))
        version_count = db.scalar(select(func.count()).select_from(DocumentVersionRecord))

    assert response.status_code == 422
    assert response.json()["detail"]["stage"] == "cover_letter_validation"
    assert response.json()["detail"]["status"] == "rolled_back"
    assert document_count == 0
    assert version_count == 0


def test_atomic_pack_rolls_back_database_mutations_when_commit_stage_fails(
    pack_client,
    monkeypatch,
) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)
    monkeypatch.setattr(
        "app.api.documents.validate_generated_document",
        lambda **kwargs: validation_report(kwargs["document_type"]),
    )
    persist = documents_api.persist_pack_document

    def fail_cover_persist(**kwargs):
        if kwargs["document_type"] == "cover_letter":
            raise HTTPException(status_code=409, detail="Simulated cover persistence failure")
        return persist(**kwargs)

    monkeypatch.setattr("app.api.documents.persist_pack_document", fail_cover_persist)

    response = client.post(
        "/documents/packs",
        json=pack_request(resume_template_id, cover_template_id),
    )

    with testing_session_local() as db:
        document_count = db.scalar(select(func.count()).select_from(DocumentRecord))
        version_count = db.scalar(select(func.count()).select_from(DocumentVersionRecord))
        job_count = db.scalar(select(func.count()).select_from(DocumentPackJobRecord))

    assert response.status_code == 409
    assert document_count == 0
    assert version_count == 0
    assert job_count == 0


@pytest.mark.parametrize("include_cover", [True, False])
def test_explicit_partial_pack_saves_only_validated_cv(
    pack_client,
    monkeypatch,
    include_cover: bool,
) -> None:
    client, testing_session_local = pack_client
    resume_template_id, cover_template_id = upload_pack_templates(client)

    def validate(**kwargs):
        if kwargs["document_type"] == "cover_letter":
            raise DocumentValidationError("Cover letter validation failed")
        return validation_report(kwargs["document_type"])

    monkeypatch.setattr("app.api.documents.validate_generated_document", validate)
    request = pack_request(
        resume_template_id,
        cover_template_id,
        persistence_mode="partial",
        include_cover=include_cover,
    )

    response = client.post("/documents/packs", json=request)

    with testing_session_local() as db:
        records = db.scalars(select(DocumentRecord)).all()
        job = db.get(DocumentPackJobRecord, "pack-job-1")

    assert response.status_code == 201
    assert response.json()["status"] == "partial"
    assert len(response.json()["documents"]) == 1
    assert response.json()["documents"][0]["type"] == "tailored_resume"
    assert [record.type for record in records] == ["tailored_resume"]
    assert job is not None
    assert job.status == "partial"
