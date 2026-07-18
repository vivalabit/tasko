from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.applications import CandidateConfirmationRecord, StoredApplicationRecord
from app.models.documents import DocumentTemplateRecord
from app.models.jobs import JobMatchRecord, StoredJobRecord
from app.models.profile import ProfileRecord
from app.services.ai_match import MATCHER_VERSION
from app.services.generation_context import (
    GenerationContextError,
    load_authoritative_generation_context,
)
from app.services.job_match_store import APPLICATION_GUIDE_STORAGE_KEY


def generation_context_session(*, include_confirmation: bool = True) -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = Session(engine)
    now = datetime.now(UTC)
    records = [
        StoredApplicationRecord(
            id="application-context",
            data={
                "id": "application-context",
                "status": "draft",
                "job": {"id": "job-context", "title": "Client vacancy copy"},
            },
        ),
        StoredJobRecord(
            id="job-context",
            data={
                "id": "job-context",
                "title": "Platform Engineer",
                "company": "Acme",
            },
        ),
        ProfileRecord(
            id="default",
            data={
                "name": "Alex",
                "skills": "Python",
                "experience": "Built production Python services.",
            },
        ),
        JobMatchRecord(
            id="match-context",
            job_id="job-context",
            profile_hash="profile-context",
            matcher_version=MATCHER_VERSION,
            cache_key="cache-context",
            score=88,
            source="openclaw",
            confidence="high",
            breakdown={
                APPLICATION_GUIDE_STORAGE_KEY: {
                    "language": "German",
                    "clarificationQuestions": [
                        {
                            "id": "production-python",
                            "requirement": "Production Python",
                            "question": "Have you used Python in production?",
                            "blocking": True,
                        }
                    ],
                    "evidenceMatrix": [],
                }
            },
            reasons=[],
            gaps=[],
            heuristic_score=88,
            created_at=now,
        ),
        DocumentTemplateRecord(
            id="template-context",
            type="cover_letter",
            name="Cover letter",
            file_name="cover.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=b"docx",
            extracted_text="Original cover letter",
            created_at=now,
            updated_at=now,
        ),
    ]
    if include_confirmation:
        records.append(
            CandidateConfirmationRecord(
                application_id="application-context",
                question_id="production-python",
                requirement="Stale client requirement",
                response="yes",
                example_text="Built two production Python services.",
                blocking=False,
                updated_at=now,
            )
        )
    db.add_all(records)
    db.commit()
    return db


def test_loads_complete_authoritative_generation_context() -> None:
    with generation_context_session() as db:
        context = load_authoritative_generation_context(
            db,
            application_id="application-context",
            template_id="template-context",
            document_type="cover_letter",
            expected_job_id="job-context",
        )

        assert context.application["status"] == "draft"
        assert context.vacancy["title"] == "Platform Engineer"
        assert context.profile["skills"] == "Python"
        assert context.application_guide["language"] == "German"
        assert context.language == "German"
        assert context.template.id == "template-context"
        assert context.confirmations[0].requirement == "Production Python"
        assert context.confirmations[0].blocking is True


def test_rejects_generation_when_required_confirmation_is_missing() -> None:
    with generation_context_session(include_confirmation=False) as db:
        with pytest.raises(
            GenerationContextError,
            match="Required candidate confirmations are incomplete",
        ):
            load_authoritative_generation_context(
                db,
                application_id="application-context",
                template_id="template-context",
                document_type="cover_letter",
            )
