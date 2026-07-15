from collections.abc import Generator
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.applications import StoredApplicationRecord
from app.models.documents import DocumentAttachmentRecord, DocumentVersionRecord


def test_document_versions_download_and_application_attachments() -> None:
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
        db.add(
            StoredApplicationRecord(
                id="application-one",
                data={"id": "application-one", "status": "applied"},
            )
        )
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        created = client.post(
            "/documents",
            json={
                "type": "cover_letter",
                "title": "Figma cover letter",
                "content": "Dear Hiring Team,\n\nI am applying for the role.",
                "jobId": "job-figma",
                "applicationId": "application-one",
            },
        )
        document_id = created.json()["id"]
        updated = client.patch(
            f"/documents/{document_id}",
            json={"content": "Dear Hiring Team,\n\nUpdated evidence-based letter."},
        )
        restored = client.post(
            f"/documents/{document_id}/restore",
            json={"version": 1},
        )
        listed = client.get("/documents?jobId=job-figma")
        downloaded = client.get(f"/documents/{document_id}/download?version=2")
        detached = client.delete(
            f"/documents/{document_id}/attachments/application-one"
        )
        deleted = client.delete(f"/documents/{document_id}")

        with testing_session_local() as db:
            version_count = db.scalar(select(func.count()).select_from(DocumentVersionRecord))
            attachment_count = db.scalar(
                select(func.count()).select_from(DocumentAttachmentRecord)
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["currentVersion"] == 1
    assert created.json()["applicationIds"] == ["application-one"]
    assert updated.status_code == 200
    assert updated.json()["currentVersion"] == 2
    assert len(updated.json()["versions"]) == 2
    assert restored.status_code == 200
    assert restored.json()["currentVersion"] == 3
    assert restored.json()["versions"][-1]["content"].startswith("Dear Hiring Team")
    assert listed.status_code == 200
    assert listed.json()[0]["jobId"] == "job-figma"
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "Figma-cover-letter-v2.docx" in downloaded.headers["content-disposition"]
    rendered_document = Document(BytesIO(downloaded.content))
    rendered_text = "\n".join(paragraph.text for paragraph in rendered_document.paragraphs)
    assert "Updated evidence-based letter." in rendered_text
    assert detached.status_code == 204
    assert deleted.status_code == 204
    assert version_count == 0
    assert attachment_count == 0


def test_document_attachment_requires_existing_application() -> None:
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

    try:
        response = client.post(
            "/documents",
            json={
                "type": "tailored_resume",
                "title": "Resume for Stripe",
                "content": "# Experience\nVerified achievements",
                "applicationId": "missing-application",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"
