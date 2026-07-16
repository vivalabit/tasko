import base64
import re
from io import BytesIO
from uuid import uuid4

from docx import Document
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.database import get_db
from app.models.applications import StoredApplicationRecord
from app.models.documents import (
    DocumentAttachRequest,
    DocumentAttachmentRecord,
    DocumentCreateRequest,
    DocumentFileRecord,
    DocumentPayload,
    DocumentRecord,
    DocumentRestoreRequest,
    DocumentTemplateCreateRequest,
    DocumentTemplatePayload,
    DocumentTemplateRecord,
    DocumentUpdateRequest,
    DocumentVersionPayload,
    DocumentVersionRecord,
    utc_now,
)
from app.services.document_export import build_document_docx, build_document_from_template

router = APIRouter()

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_TEMPLATE_BYTES = 10_000_000


@router.get("", response_model=list[DocumentPayload])
def list_documents(
    job_id: str | None = Query(default=None, alias="jobId"),
    application_id: str | None = Query(default=None, alias="applicationId"),
    db: Session = Depends(get_db),
) -> list[DocumentPayload]:
    try:
        statement = (
            select(DocumentRecord)
            .options(
                selectinload(DocumentRecord.versions),
                selectinload(DocumentRecord.attachments),
            )
            .order_by(DocumentRecord.updated_at.desc())
        )
        if job_id is not None:
            statement = statement.where(DocumentRecord.job_id == job_id)
        if application_id is not None:
            statement = statement.join(DocumentAttachmentRecord).where(
                DocumentAttachmentRecord.application_id == application_id
            )
        return [document_payload(record) for record in db.scalars(statement).unique().all()]
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.post("", response_model=DocumentPayload, status_code=status.HTTP_201_CREATED)
def create_document(
    request: DocumentCreateRequest,
    db: Session = Depends(get_db),
) -> DocumentPayload:
    try:
        now = utc_now()
        document_id = str(uuid4())
        record = DocumentRecord(
            id=document_id,
            type=request.type,
            title=request.title.strip(),
            job_id=request.job_id,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
        record.versions.append(
            DocumentVersionRecord(
                id=str(uuid4()),
                document_id=document_id,
                version=1,
                content=request.content,
                created_at=now,
            )
        )
        db.add(record)
        db.flush()
        if request.template_id:
            template = require_template(db, request.template_id)
            if template.type != request.type:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Document template type does not match document type",
                )
            try:
                rendered_content = build_document_from_template(
                    template_content=template.content,
                    content=request.content,
                    document_type=request.type,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                ) from exc
            db.add(
                DocumentFileRecord(
                    id=str(uuid4()),
                    document_id=document_id,
                    version=1,
                    template_id=template.id,
                    content=rendered_content,
                    created_at=now,
                )
            )
        if request.application_id:
            attach_document_record(db, record, request.application_id)
        db.commit()
        return document_payload(require_document(db, document_id))
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.get("/{document_id}", response_model=DocumentPayload)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentPayload:
    try:
        return document_payload(require_document(db, document_id))
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.patch("/{document_id}", response_model=DocumentPayload)
def update_document(
    document_id: str,
    request: DocumentUpdateRequest,
    db: Session = Depends(get_db),
) -> DocumentPayload:
    try:
        record = require_document(db, document_id)
        fields = request.model_fields_set
        if "title" in fields and request.title is not None:
            record.title = request.title.strip()
        if "job_id" in fields:
            record.job_id = request.job_id
        if "content" in fields and request.content is not None:
            current = current_version_record(record)
            if current.content != request.content:
                next_version = record.current_version + 1
                record.versions.append(
                    DocumentVersionRecord(
                        id=str(uuid4()),
                        document_id=record.id,
                        version=next_version,
                        content=request.content,
                        created_at=utc_now(),
                    )
                )
                current_file = document_file_record(db, record.id, record.current_version)
                if current_file and current_file.template_id:
                    template = require_template(db, current_file.template_id)
                    try:
                        rendered_content = build_document_from_template(
                            template_content=template.content,
                            content=request.content,
                            document_type=record.type,
                        )
                    except ValueError as exc:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=str(exc),
                        ) from exc
                    db.add(
                        DocumentFileRecord(
                            id=str(uuid4()),
                            document_id=record.id,
                            version=next_version,
                            template_id=template.id,
                            content=rendered_content,
                            created_at=utc_now(),
                        )
                    )
                record.current_version = next_version
        record.updated_at = utc_now()
        db.commit()
        return document_payload(require_document(db, document_id))
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.post("/{document_id}/restore", response_model=DocumentPayload)
def restore_document_version(
    document_id: str,
    request: DocumentRestoreRequest,
    db: Session = Depends(get_db),
) -> DocumentPayload:
    try:
        record = require_document(db, document_id)
        source = next(
            (version for version in record.versions if version.version == request.version),
            None,
        )
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document version not found",
            )
        next_version = record.current_version + 1
        record.versions.append(
            DocumentVersionRecord(
                id=str(uuid4()),
                document_id=record.id,
                version=next_version,
                content=source.content,
                created_at=utc_now(),
            )
        )
        source_file = document_file_record(db, record.id, source.version)
        if source_file:
            db.add(
                DocumentFileRecord(
                    id=str(uuid4()),
                    document_id=record.id,
                    version=next_version,
                    template_id=source_file.template_id,
                    content=source_file.content,
                    created_at=utc_now(),
                )
            )
        record.current_version = next_version
        record.updated_at = utc_now()
        db.commit()
        return document_payload(require_document(db, document_id))
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.post("/{document_id}/attachments", response_model=DocumentPayload)
def attach_document(
    document_id: str,
    request: DocumentAttachRequest,
    db: Session = Depends(get_db),
) -> DocumentPayload:
    try:
        record = require_document(db, document_id)
        attach_document_record(db, record, request.application_id)
        record.updated_at = utc_now()
        db.commit()
        return document_payload(require_document(db, document_id))
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete(
    "/{document_id}/attachments/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def detach_document(
    document_id: str,
    application_id: str,
    db: Session = Depends(get_db),
) -> None:
    try:
        record = require_document(db, document_id)
        attachment = next(
            (
                item
                for item in record.attachments
                if item.application_id == application_id
            ),
            None,
        )
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document attachment not found",
            )
        db.delete(attachment)
        record.updated_at = utc_now()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.get("/{document_id}/download")
def download_document(
    document_id: str,
    version: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> Response:
    try:
        record = require_document(db, document_id)
        selected_version = (
            next((item for item in record.versions if item.version == version), None)
            if version is not None
            else current_version_record(record)
        )
        if not selected_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document version not found",
            )
        rendered_file = document_file_record(db, record.id, selected_version.version)
        content = rendered_file.content if rendered_file else build_document_docx(
            title=record.title,
            content=selected_version.content,
            document_type=record.type,
            version=selected_version.version,
        )
        filename = safe_filename(record.title)
        return Response(
            content=content,
            media_type=(
                DOCX_CONTENT_TYPE
            ),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}-v{selected_version.version}.docx"'
            },
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.get("/templates/library", response_model=list[DocumentTemplatePayload])
def list_document_templates(db: Session = Depends(get_db)) -> list[DocumentTemplatePayload]:
    try:
        records = db.scalars(
            select(DocumentTemplateRecord).order_by(DocumentTemplateRecord.updated_at.desc())
        ).all()
        return [document_template_payload(record) for record in records]
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.post(
    "/templates",
    response_model=DocumentTemplatePayload,
    status_code=status.HTTP_201_CREATED,
)
def create_document_template(
    request: DocumentTemplateCreateRequest,
    db: Session = Depends(get_db),
) -> DocumentTemplatePayload:
    if not request.file_name.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template must be a .docx file",
        )
    content_type, content = decode_data_url(request.data_url)
    if not content or len(content) > MAX_TEMPLATE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Template must be a non-empty DOCX file under 10 MB",
        )
    try:
        document = Document(BytesIO(content))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template is not a valid DOCX file",
        ) from exc

    extracted_text = "\n".join(
        paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()
    )
    now = utc_now()
    record = DocumentTemplateRecord(
        id=str(uuid4()),
        type=request.type,
        name=request.name.strip(),
        file_name=safe_upload_filename(request.file_name),
        content_type=content_type or DOCX_CONTENT_TYPE,
        content=content,
        extracted_text=extracted_text,
        created_at=now,
        updated_at=now,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return document_template_payload(record)
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_template(template_id: str, db: Session = Depends(get_db)) -> None:
    try:
        template = require_template(db, template_id)
        db.delete(template)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> None:
    try:
        record = require_document(db, document_id)
        db.delete(record)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise database_unavailable(exc) from exc


def require_document(db: Session, document_id: str) -> DocumentRecord:
    record = db.scalar(
        select(DocumentRecord)
        .where(DocumentRecord.id == document_id)
        .options(
            selectinload(DocumentRecord.versions),
            selectinload(DocumentRecord.attachments),
        )
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return record


def require_template(db: Session, template_id: str) -> DocumentTemplateRecord:
    record = db.get(DocumentTemplateRecord, template_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document template not found",
        )
    return record


def document_file_record(
    db: Session,
    document_id: str,
    version: int,
) -> DocumentFileRecord | None:
    return db.scalar(
        select(DocumentFileRecord).where(
            DocumentFileRecord.document_id == document_id,
            DocumentFileRecord.version == version,
        )
    )


def attach_document_record(
    db: Session,
    document: DocumentRecord,
    application_id: str,
) -> None:
    if not db.get(StoredApplicationRecord, application_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    if any(item.application_id == application_id for item in document.attachments):
        return
    document.attachments.append(
        DocumentAttachmentRecord(
            id=str(uuid4()),
            document_id=document.id,
            application_id=application_id,
            created_at=utc_now(),
        )
    )


def current_version_record(record: DocumentRecord) -> DocumentVersionRecord:
    current = next(
        (version for version in record.versions if version.version == record.current_version),
        None,
    )
    if not current:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document has no current version",
        )
    return current


def document_payload(record: DocumentRecord) -> DocumentPayload:
    return DocumentPayload(
        id=record.id,
        type=record.type,
        title=record.title,
        job_id=record.job_id,
        application_ids=[item.application_id for item in record.attachments],
        current_version=record.current_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        versions=[
            DocumentVersionPayload(
                id=version.id,
                version=version.version,
                content=version.content,
                created_at=version.created_at,
            )
            for version in record.versions
        ],
    )


def safe_filename(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return normalized[:120] or "tasko-document"


def safe_upload_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]+", "-", value.strip())[:240] or "template.docx"


def decode_data_url(value: str) -> tuple[str, bytes]:
    header, separator, payload = value.partition(",")
    if not separator:
        return "", b""
    content_type = header.removeprefix("data:").split(";")[0]
    try:
        if ";base64" in header:
            return content_type, base64.b64decode(payload, validate=False)
        return content_type, payload.encode()
    except (ValueError, TypeError):
        return content_type, b""


def document_template_payload(record: DocumentTemplateRecord) -> DocumentTemplatePayload:
    return DocumentTemplatePayload(
        id=record.id,
        type=record.type,
        name=record.name,
        file_name=record.file_name,
        extracted_text=record.extracted_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def database_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Documents database is unavailable",
    )
