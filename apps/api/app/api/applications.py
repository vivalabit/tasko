from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.models.applications import (
    CandidateConfirmationInput,
    CandidateConfirmationPayload,
    CandidateConfirmationRecord,
    CandidateConfirmationsRequest,
    StoredApplicationEventPayload,
    StoredApplicationEventRecord,
    StoredApplicationEventsRequest,
    StoredApplicationPayload,
    StoredApplicationRecord,
    StoredApplicationsRequest,
)
from app.models.jobs import JobMatchRecord
from app.services.ai_match import MATCHER_VERSION
from app.services.job_match_store import match_record_to_ai_match

router = APIRouter()


@dataclass(frozen=True)
class StoredClarificationQuestion:
    requirement: str
    blocking: bool


def is_meaningful_confirmation(confirmation: CandidateConfirmationInput) -> bool:
    if confirmation.response == "no":
        return True
    normalized = " ".join(confirmation.example_text.split())
    words = [
        word for word in normalized.split(" ") if any(character.isalnum() for character in word)
    ]
    return len(normalized) >= 10 and len(words) >= 2


def confirmation_payload(record: CandidateConfirmationRecord) -> CandidateConfirmationPayload:
    return CandidateConfirmationPayload(
        questionId=record.question_id,
        requirement=record.requirement,
        response=record.response,
        exampleText=record.example_text,
        blocking=record.blocking,
        updatedAt=record.updated_at,
    )


def stored_clarification_questions(
    db: Session,
    application: StoredApplicationRecord,
) -> dict[str, StoredClarificationQuestion]:
    application_data = application.data if isinstance(application.data, dict) else {}
    job = application_data.get("job")
    job_id = str(job.get("id") or "").strip() if isinstance(job, dict) else ""
    if not job_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application does not reference a job with a stored ai-match-v3",
        )

    match_record = (
        db.query(JobMatchRecord)
        .filter(
            JobMatchRecord.job_id == job_id,
            JobMatchRecord.matcher_version == MATCHER_VERSION,
        )
        .order_by(JobMatchRecord.created_at.desc(), JobMatchRecord.id.desc())
        .first()
    )
    if not match_record:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored ai-match-v3 is required before saving candidate confirmations",
        )

    application_guide = match_record_to_ai_match(match_record).get("applicationGuide")
    if not isinstance(application_guide, dict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored ai-match-v3 application guide is unavailable",
        )

    raw_questions = application_guide.get("clarificationQuestions")
    questions: dict[str, StoredClarificationQuestion] = {}
    if not isinstance(raw_questions, list):
        return questions

    for raw_question in raw_questions:
        if not isinstance(raw_question, dict):
            continue
        question_id = str(raw_question.get("id") or "").strip()
        question_text = str(raw_question.get("question") or "").strip()
        requirement = str(raw_question.get("requirement") or question_text).strip()[:500]
        if not question_id or not requirement:
            continue
        if question_id in questions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stored ai-match-v3 contains duplicate clarification question IDs",
            )
        questions[question_id] = StoredClarificationQuestion(
            requirement=requirement,
            blocking=bool(raw_question.get("blocking")),
        )
    return questions


@router.get("", response_model=list[StoredApplicationPayload])
def list_applications(db: Session = Depends(get_db)) -> list[StoredApplicationPayload]:
    try:
        records = db.query(StoredApplicationRecord).order_by(StoredApplicationRecord.id.desc()).all()
        return [StoredApplicationPayload(id=record.id, data=record.data) for record in records]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Applications database is unavailable",
        ) from exc


@router.put("", response_model=list[StoredApplicationPayload])
def upsert_applications(
    request: StoredApplicationsRequest,
    db: Session = Depends(get_db),
) -> list[StoredApplicationPayload]:
    try:
        for application in request.applications:
            record = db.get(StoredApplicationRecord, application.id)
            if record:
                record.data = application.data
            else:
                db.add(StoredApplicationRecord(id=application.id, data=application.data))

        db.commit()
        return list_applications(db)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Applications database is unavailable",
        ) from exc


@router.get(
    "/{application_id}/confirmations",
    response_model=list[CandidateConfirmationPayload],
)
def list_candidate_confirmations(
    application_id: str,
    db: Session = Depends(get_db),
) -> list[CandidateConfirmationPayload]:
    try:
        if not db.get(StoredApplicationRecord, application_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        records = (
            db.query(CandidateConfirmationRecord)
            .filter(CandidateConfirmationRecord.application_id == application_id)
            .order_by(CandidateConfirmationRecord.question_id)
            .all()
        )
        return [confirmation_payload(record) for record in records]
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Candidate confirmations are unavailable",
        ) from exc


@router.put(
    "/{application_id}/confirmations",
    response_model=list[CandidateConfirmationPayload],
)
def replace_candidate_confirmations(
    application_id: str,
    request: CandidateConfirmationsRequest,
    db: Session = Depends(get_db),
) -> list[CandidateConfirmationPayload]:
    try:
        application = db.get(StoredApplicationRecord, application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        questions_by_id = stored_clarification_questions(db, application)

        question_ids = [confirmation.question_id for confirmation in request.confirmations]
        if len(question_ids) != len(set(question_ids)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Candidate confirmation question IDs must be unique",
            )

        unknown_question_ids = set(question_ids) - set(questions_by_id)
        if unknown_question_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "Unknown candidate confirmation question IDs: "
                    f"{', '.join(sorted(unknown_question_ids))}"
                ),
            )
        required_question_ids = {
            question_id for question_id, question in questions_by_id.items() if question.blocking
        }
        missing_required_ids = required_question_ids - set(question_ids)
        if missing_required_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Required candidate confirmations are missing: {', '.join(sorted(missing_required_ids))}",
            )

        for confirmation in request.confirmations:
            question = questions_by_id[confirmation.question_id]
            if question.blocking and not is_meaningful_confirmation(confirmation):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        f"A meaningful example is required for {question.requirement} "
                        "when the answer is yes or partial"
                    ),
                )

        existing_records = {
            record.question_id: record
            for record in db.query(CandidateConfirmationRecord)
            .filter(CandidateConfirmationRecord.application_id == application_id)
            .all()
        }
        now = datetime.now(UTC)
        requested_ids = set(question_ids)

        for question_id, record in existing_records.items():
            if question_id not in requested_ids:
                db.delete(record)

        for confirmation in request.confirmations:
            question = questions_by_id[confirmation.question_id]
            example_text = confirmation.example_text.strip()
            record = existing_records.get(confirmation.question_id)
            if record:
                has_changed = (
                    record.requirement != question.requirement
                    or record.response != confirmation.response
                    or record.example_text != example_text
                    or record.blocking != question.blocking
                )
                record.requirement = question.requirement
                record.response = confirmation.response
                record.example_text = example_text
                record.blocking = question.blocking
                if has_changed:
                    record.updated_at = now
            else:
                db.add(
                    CandidateConfirmationRecord(
                        application_id=application_id,
                        question_id=confirmation.question_id,
                        requirement=question.requirement,
                        response=confirmation.response,
                        example_text=example_text,
                        blocking=question.blocking,
                        updated_at=now,
                    )
                )

        db.commit()
        return list_candidate_confirmations(application_id, db)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Candidate confirmations could not be saved",
        ) from exc


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: str, db: Session = Depends(get_db)) -> None:
    try:
        record = db.get(StoredApplicationRecord, application_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

        related_events = (
            db.query(StoredApplicationEventRecord)
            .filter(StoredApplicationEventRecord.application_id == application_id)
            .all()
        )
        for event in related_events:
            db.delete(event)

        db.query(CandidateConfirmationRecord).filter(
            CandidateConfirmationRecord.application_id == application_id
        ).delete()

        db.delete(record)
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Applications database is unavailable",
        ) from exc


@router.get("/events", response_model=list[StoredApplicationEventPayload])
def list_application_events(db: Session = Depends(get_db)) -> list[StoredApplicationEventPayload]:
    try:
        records = db.query(StoredApplicationEventRecord).order_by(StoredApplicationEventRecord.id.desc()).all()
        return [
            StoredApplicationEventPayload(id=record.id, application_id=record.application_id, data=record.data)
            for record in records
        ]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application events database is unavailable",
        ) from exc


@router.put("/events", response_model=list[StoredApplicationEventPayload])
def upsert_application_events(
    request: StoredApplicationEventsRequest,
    db: Session = Depends(get_db),
) -> list[StoredApplicationEventPayload]:
    try:
        for event in request.events:
            record = db.get(StoredApplicationEventRecord, event.id)
            if record:
                record.application_id = event.application_id
                record.data = event.data
            else:
                db.add(StoredApplicationEventRecord(id=event.id, application_id=event.application_id, data=event.data))

        db.commit()
        return list_application_events(db)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application events database is unavailable",
        ) from exc


@router.patch("/events/{event_id}", response_model=StoredApplicationEventPayload)
def update_application_event(
    event_id: str,
    event: StoredApplicationEventPayload,
    db: Session = Depends(get_db),
) -> StoredApplicationEventPayload:
    if event.id != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application event id does not match request path",
        )

    try:
        record = db.get(StoredApplicationEventRecord, event_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application event not found",
            )

        record.application_id = event.application_id
        record.data = event.data
        db.commit()
        db.refresh(record)
        return StoredApplicationEventPayload(id=record.id, application_id=record.application_id, data=record.data)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application events database is unavailable",
        ) from exc


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application_event(event_id: str, db: Session = Depends(get_db)) -> None:
    try:
        record = db.get(StoredApplicationEventRecord, event_id)
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application event not found",
            )

        db.delete(record)
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application events database is unavailable",
        ) from exc
