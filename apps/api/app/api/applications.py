from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.models.applications import (
    StoredApplicationEventPayload,
    StoredApplicationEventRecord,
    StoredApplicationEventsRequest,
    StoredApplicationPayload,
    StoredApplicationRecord,
    StoredApplicationsRequest,
)

router = APIRouter()


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
