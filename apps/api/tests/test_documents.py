from collections.abc import Generator
import base64
from io import BytesIO
import json
import zipfile

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.applications import StoredApplicationRecord
from app.models.documents import (
    DocumentAttachmentRecord,
    DocumentGenerationProvenanceRecord,
    DocumentVersionGenerationProvenanceRecord,
    DocumentVersionRecord,
)


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
                "generationFingerprint": "a" * 64,
                "generationModel": "openai/gpt-5.6-terra",
                "inputVersions": {
                    "fingerprintVersion": "generation-fingerprint-v1",
                    "vacancy": "vacancy-v1",
                    "profile": "profile-v2",
                    "applicationGuide": "guide-v3",
                    "sourceDocument": {"id": "source-one", "fingerprint": "docx-v1"},
                    "language": "english-v1",
                    "confirmations": "confirmations-v2",
                },
            },
        )
        document_id = created.json()["id"]
        updated = client.patch(
            f"/documents/{document_id}",
            json={
                "content": "Dear Hiring Team,\n\nUpdated evidence-based letter.",
                "generationFingerprint": "b" * 64,
                "generationModel": "openai/gpt-5.7",
                "inputVersions": {
                    "fingerprintVersion": "generation-fingerprint-v1",
                    "vacancy": "vacancy-v2",
                },
            },
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
            provenance_count = db.scalar(
                select(func.count()).select_from(DocumentGenerationProvenanceRecord)
            )
            version_provenance_count = db.scalar(
                select(func.count()).select_from(
                    DocumentVersionGenerationProvenanceRecord
                )
            )
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert created.json()["currentVersion"] == 1
    assert created.json()["applicationIds"] == ["application-one"]
    assert created.json()["generationFingerprint"] == "a" * 64
    assert created.json()["generationModel"] == "openai/gpt-5.6-terra"
    assert created.json()["inputVersions"]["applicationGuide"] == "guide-v3"
    assert updated.status_code == 200
    assert updated.json()["id"] == document_id
    assert updated.json()["currentVersion"] == 2
    assert len(updated.json()["versions"]) == 2
    assert updated.json()["applicationIds"] == ["application-one"]
    assert updated.json()["generationFingerprint"] == "b" * 64
    assert updated.json()["generationModel"] == "openai/gpt-5.7"
    assert restored.status_code == 200
    assert restored.json()["id"] == document_id
    assert restored.json()["currentVersion"] == 3
    assert restored.json()["versions"][-1]["content"].startswith("Dear Hiring Team")
    assert restored.json()["applicationIds"] == ["application-one"]
    assert restored.json()["generationFingerprint"] == "a" * 64
    assert listed.status_code == 200
    assert listed.json()[0]["jobId"] == "job-figma"
    assert listed.json()[0]["generationFingerprint"] == "a" * 64
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
    assert provenance_count == 0
    assert version_provenance_count == 0


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
        incomplete_provenance = client.post(
            "/documents",
            json={
                "type": "tailored_resume",
                "title": "Incomplete provenance",
                "content": "Verified achievements",
                "generationFingerprint": "b" * 64,
            },
        )
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

    assert incomplete_provenance.status_code == 422
    assert "must be provided together" in incomplete_provenance.json()["detail"]
    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_cover_letter_template_preserves_visual_structure() -> None:
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
                id="application-template",
                data={"id": "application-template", "status": "draft"},
            )
        )
        db.commit()

    template = Document()
    template.sections[0].header.paragraphs[0].text = "EDUARD · SOFTWARE ENGINEER"
    template.add_paragraph("Dear Hiring Team,")
    body = template.add_paragraph("Original reusable body paragraph.")
    body.style = template.styles["Normal"]
    template.add_paragraph("Kind regards,")
    template.add_paragraph("Eduard")
    template.sections[0].footer.paragraphs[0].text = "Private application"
    template_output = BytesIO()
    template.save(template_output)
    data_url = "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64," + base64.b64encode(
        template_output.getvalue()
    ).decode()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        uploaded = client.post(
            "/documents/templates",
            json={
                "type": "cover_letter",
                "name": "My cover letter",
                "fileName": "cover-letter.docx",
                "dataUrl": data_url,
            },
        )
        template_id = uploaded.json()["id"]
        listed = client.get("/documents/templates/library")
        created = client.post(
            "/documents",
            json={
                "type": "cover_letter",
                "title": "Generated cover letter",
                "content": (
                    "Dear Acme Hiring Team,\n\n"
                    "My first tailored paragraph.\n\n"
                    "My second tailored paragraph.\n\n"
                    "Kind regards,\n\nEduard"
                ),
                "jobId": "job-acme",
                "applicationId": "application-template",
                "templateId": template_id,
            },
        )
        downloaded = client.get(f"/documents/{created.json()['id']}/download")
    finally:
        app.dependency_overrides.clear()

    rendered = Document(BytesIO(downloaded.content))
    body_text = "\n".join(paragraph.text for paragraph in rendered.paragraphs)
    header_text = rendered.sections[0].header.paragraphs[0].text
    footer_text = rendered.sections[0].footer.paragraphs[0].text

    assert uploaded.status_code == 201
    assert listed.status_code == 200
    assert listed.json()[0]["fileName"] == "cover-letter.docx"
    assert created.status_code == 201
    assert downloaded.status_code == 200
    assert header_text == "EDUARD · SOFTWARE ENGINEER"
    assert footer_text == "Private application"
    assert "My first tailored paragraph." in body_text
    assert "My second tailored paragraph." in body_text
    assert "Original reusable body paragraph." not in body_text


def test_resume_template_rewrites_blocks_without_rebuilding_design() -> None:
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
                id="application-resume-template",
                data={"id": "application-resume-template", "status": "draft"},
            )
        )
        db.commit()

    template = Document()
    template.sections[0].header.paragraphs[0].text = "EDUARD · CONTACT"
    name = template.add_paragraph("Eduard Ishchenko")
    name.style = template.styles["Heading 1"]
    template.add_paragraph("Original professional summary with verified delivery experience.")
    table = template.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.cell(0, 0).text = "Python"
    table.cell(0, 1).text = "Original achievement"
    template.sections[0].footer.paragraphs[0].text = "Resume footer"
    template_output = BytesIO()
    template.save(template_output)
    data_url = "data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64," + base64.b64encode(
        template_output.getvalue()
    ).decode()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        uploaded = client.post(
            "/documents/templates",
            json={
                "type": "tailored_resume",
                "name": "Main CV",
                "fileName": "resume.docx",
                "dataUrl": data_url,
            },
        )
        created = client.post(
            "/documents",
            json={
                "type": "tailored_resume",
                "title": "Tailored resume",
                "content": json.dumps(
                    {
                        "replacements": [
                            {
                                "blockId": "block-0002",
                                "original": "Original professional summary with verified delivery experience.",
                                "replacement": "Backend engineer focused on FastAPI",
                                "reason": "Matches the target role with verified profile evidence",
                            },
                            {
                                "blockId": "block-0004",
                                "original": "Original achievement",
                                "replacement": "Built a verified production service",
                                "reason": "Uses a verified achievement",
                            },
                        ]
                    }
                ),
                "applicationId": "application-resume-template",
                "templateId": uploaded.json()["id"],
            },
        )
        downloaded = client.get(f"/documents/{created.json()['id']}/download")
    finally:
        app.dependency_overrides.clear()

    rendered = Document(BytesIO(downloaded.content))
    with zipfile.ZipFile(BytesIO(template_output.getvalue())) as source_package:
        with zipfile.ZipFile(BytesIO(downloaded.content)) as rendered_package:
            for preserved_part in (
                "word/styles.xml",
                "word/header1.xml",
                "word/footer1.xml",
            ):
                assert rendered_package.read(preserved_part) == source_package.read(preserved_part)
            assert rendered_package.read("word/document.xml") != source_package.read(
                "word/document.xml"
            )

    assert uploaded.status_code == 201
    assert created.status_code == 201
    assert downloaded.status_code == 200
    assert rendered.sections[0].header.paragraphs[0].text == "EDUARD · CONTACT"
    assert rendered.sections[0].footer.paragraphs[0].text == "Resume footer"
    assert rendered.paragraphs[0].style.name == "Heading 1"
    assert rendered.paragraphs[1].text == "Backend engineer focused on FastAPI"
    assert rendered.tables[0].style.name == "Table Grid"
    assert rendered.tables[0].cell(0, 0).text == "Python"
    assert rendered.tables[0].cell(0, 1).text == "Built a verified production service"
