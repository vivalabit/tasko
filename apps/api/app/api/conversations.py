from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import get_db
from app.core.identity import bind_request_identity
from app.models.conversations import (
    ConversationPayload,
    ConversationRecord,
    ConversationUpdateRequest,
    ConversationUpsertRequest,
    MessagePayload,
    MessageRecord,
    MessageUpsertRequest,
    utc_now,
)

router = APIRouter(dependencies=[Depends(bind_request_identity)])


@router.get("", response_model=list[ConversationPayload])
def list_conversations(
    archived: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ConversationPayload]:
    try:
        records = db.scalars(
            select(ConversationRecord)
            .where(ConversationRecord.archived.is_(archived))
            .options(selectinload(ConversationRecord.messages))
            .order_by(ConversationRecord.updated_at.desc())
        ).all()
        return [conversation_payload(record) for record in records]
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.get("/{conversation_id}", response_model=ConversationPayload)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationPayload:
    try:
        return conversation_payload(require_conversation(db, conversation_id))
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.put("/{conversation_id}", response_model=ConversationPayload)
def upsert_conversation(
    conversation_id: str,
    request: ConversationUpsertRequest,
    db: Session = Depends(get_db),
) -> ConversationPayload:
    try:
        record = db.get(ConversationRecord, conversation_id)
        now = utc_now()
        if record:
            record.title = request.title
            record.context_kind = request.context_kind
            record.context_id = request.context_id
            record.archived = request.archived
            record.openclaw_session_key = request.openclaw_session_key
            record.updated_at = request.updated_at or now
        else:
            record = ConversationRecord(
                id=conversation_id,
                title=request.title,
                context_kind=request.context_kind,
                context_id=request.context_id,
                archived=request.archived,
                openclaw_session_key=request.openclaw_session_key,
                created_at=request.created_at or now,
                updated_at=request.updated_at or now,
            )
            db.add(record)
            db.flush()

        for sequence, message in enumerate(request.messages):
            upsert_message_record(
                db,
                conversation_id=conversation_id,
                message_id=message.id,
                role=message.role,
                content=message.content,
                source=message.source,
                message_status=message.status,
                created_at=message.created_at,
                sequence=sequence,
            )

        db.commit()
        return conversation_payload(require_conversation(db, conversation_id))
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, SQLAlchemyError) as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.patch("/{conversation_id}", response_model=ConversationPayload)
def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    db: Session = Depends(get_db),
) -> ConversationPayload:
    try:
        record = require_conversation(db, conversation_id)
        fields = request.model_fields_set
        if "title" in fields and request.title is not None:
            record.title = request.title
        if "context_kind" in fields and request.context_kind is not None:
            record.context_kind = request.context_kind
        if "context_id" in fields and request.context_id is not None:
            record.context_id = request.context_id
        if "archived" in fields and request.archived is not None:
            record.archived = request.archived
        record.updated_at = utc_now()
        db.commit()
        return conversation_payload(require_conversation(db, conversation_id))
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)) -> None:
    try:
        record = require_conversation(db, conversation_id)
        db.delete(record)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.put("/{conversation_id}/messages/{message_id}", response_model=MessagePayload)
def upsert_message(
    conversation_id: str,
    message_id: str,
    request: MessageUpsertRequest,
    db: Session = Depends(get_db),
) -> MessagePayload:
    try:
        conversation = require_conversation(db, conversation_id)
        existing = db.get(MessageRecord, message_id)
        sequence = existing.sequence if existing else next_message_sequence(db, conversation_id)
        record = upsert_message_record(
            db,
            conversation_id=conversation_id,
            message_id=message_id,
            role=request.role,
            content=request.content,
            source=request.source,
            message_status=request.status,
            created_at=request.created_at or utc_now(),
            sequence=sequence,
        )
        conversation.updated_at = utc_now()
        db.commit()
        db.refresh(record)
        return message_payload(record)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete(
    "/{conversation_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_message(
    conversation_id: str,
    message_id: str,
    db: Session = Depends(get_db),
) -> None:
    try:
        conversation = require_conversation(db, conversation_id)
        record = db.get(MessageRecord, message_id)
        if not record or record.conversation_id != conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )
        db.delete(record)
        conversation.updated_at = utc_now()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


def require_conversation(db: Session, conversation_id: str) -> ConversationRecord:
    record = db.scalar(
        select(ConversationRecord)
        .where(ConversationRecord.id == conversation_id)
        .options(selectinload(ConversationRecord.messages))
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return record


def upsert_message_record(
    db: Session,
    *,
    conversation_id: str,
    message_id: str,
    role: str,
    content: str,
    source: str | None,
    message_status: str,
    created_at: datetime,
    sequence: int,
) -> MessageRecord:
    record = db.get(MessageRecord, message_id)
    if record and record.conversation_id != conversation_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Message id already belongs to another conversation",
        )
    if not record:
        record = MessageRecord(id=message_id, conversation_id=conversation_id, sequence=sequence)
        db.add(record)
    record.role = role
    record.content = content
    record.source = source
    record.status = message_status
    record.created_at = created_at
    return record


def next_message_sequence(db: Session, conversation_id: str) -> int:
    current = db.scalar(
        select(func.max(MessageRecord.sequence)).where(
            MessageRecord.conversation_id == conversation_id
        )
    )
    return (current if current is not None else -1) + 1


def message_payload(record: MessageRecord) -> MessagePayload:
    return MessagePayload(
        id=record.id,
        role=record.role,
        content=record.content,
        source=record.source,
        status=record.status,
        created_at=record.created_at,
    )


def conversation_payload(record: ConversationRecord) -> ConversationPayload:
    return ConversationPayload(
        id=record.id,
        title=record.title,
        context_kind=record.context_kind,
        context_id=record.context_id,
        openclaw_session_key=record.openclaw_session_key,
        archived=record.archived,
        created_at=record.created_at,
        updated_at=record.updated_at,
        messages=[message_payload(message) for message in record.messages],
    )


def database_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Conversations database is unavailable",
    )
