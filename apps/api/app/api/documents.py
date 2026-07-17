import base64
import hashlib
import json
import re
from datetime import datetime
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
    DocumentGenerationProvenanceRecord,
    DocumentPackItemRequest,
    DocumentPackJobRecord,
    DocumentPackPayload,
    DocumentPackRequest,
    DocumentPackStagePayload,
    DocumentPackValidationPayload,
    DocumentPayload,
    DocumentRecord,
    DocumentRestoreRequest,
    DocumentTemplateCreateRequest,
    DocumentTemplatePayload,
    DocumentTemplateRecord,
    DocumentUpdateRequest,
    DocumentVersionGenerationProvenanceRecord,
    DocumentVersionPayload,
    DocumentVersionRecord,
    DocumentVersionValidationRecord,
    utc_now,
)
from app.services.document_export import build_document_docx, build_document_from_template
from app.services.document_validation import (
    DocumentValidationError,
    validate_generated_document,
)

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
                selectinload(DocumentRecord.generation_provenance),
                selectinload(DocumentRecord.version_validations),
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
        has_provenance = validate_generation_provenance(
            request.generation_fingerprint,
            request.generation_model,
            request.input_versions,
        )
        if has_provenance:
            set_current_generation_provenance(
                record,
                request.generation_fingerprint or "",
                request.generation_model or "",
                request.input_versions,
                now,
            )
            append_version_generation_provenance(
                record,
                1,
                request.generation_fingerprint or "",
                request.generation_model or "",
                request.input_versions,
                now,
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
            if has_provenance:
                if not request.validation_evidence:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="Validation evidence is required for generated documents",
                    )
                validation = validate_document_or_422(
                    template_content=template.content,
                    rendered_content=rendered_content,
                    generated_content=request.content,
                    document_type=request.type,
                    evidence=request.validation_evidence,
                )
                append_document_validation(record, 1, validation, now)
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


@router.post(
    "/packs/validate-resume",
    response_model=DocumentPackValidationPayload,
)
def validate_resume_pack_item(
    request: DocumentPackItemRequest,
    db: Session = Depends(get_db),
) -> DocumentPackValidationPayload:
    try:
        _, _, validation = prepare_pack_document(
            db,
            request,
            "tailored_resume",
        )
        return DocumentPackValidationPayload(validation=validation)
    except DocumentValidationError as exc:
        raise pack_validation_failed("resume_validation", exc) from exc
    except ValueError as exc:
        raise pack_validation_failed("resume_validation", exc) from exc
    except SQLAlchemyError as exc:
        raise database_unavailable(exc) from exc


@router.post(
    "/packs",
    response_model=DocumentPackPayload,
    status_code=status.HTTP_201_CREATED,
)
def create_document_pack(
    request: DocumentPackRequest,
    db: Session = Depends(get_db),
) -> DocumentPackPayload:
    request_fingerprint = document_pack_request_fingerprint(request)
    try:
        existing_job = db.get(DocumentPackJobRecord, request.pack_job_id)
        if existing_job:
            if existing_job.request_fingerprint != request_fingerprint:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Pack job ID was already used for a different request",
                )
            return document_pack_payload(existing_job, db)

        if not db.get(StoredApplicationRecord, request.application_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )
        if request.persistence_mode == "atomic" and request.cover_letter is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "stage": "cover_letter_generation",
                    "status": "rolled_back",
                    "message": "Atomic application packs require a cover letter",
                },
            )

        try:
            resume_template, resume_content, resume_validation = prepare_pack_document(
                db,
                request.resume,
                "tailored_resume",
            )
        except (DocumentValidationError, ValueError) as exc:
            raise pack_validation_failed("resume_validation", exc) from exc

        cover_prepared: tuple[DocumentTemplateRecord, bytes, dict[str, object]] | None = None
        cover_failure = ""
        if request.cover_letter is not None:
            try:
                cover_prepared = prepare_pack_document(
                    db,
                    request.cover_letter,
                    "cover_letter",
                )
            except (DocumentValidationError, ValueError) as exc:
                cover_failure = str(exc)
                if request.persistence_mode == "atomic":
                    raise pack_validation_failed("cover_letter_validation", exc) from exc
        else:
            cover_failure = request.partial_reason or "Cover letter generation did not complete"

        now = utc_now()
        document_ids = [
            persist_pack_document(
                db=db,
                item=request.resume,
                document_type="tailored_resume",
                template=resume_template,
                rendered_content=resume_content,
                validation=resume_validation,
                job_id=request.job_id,
                application_id=request.application_id,
                created_at=now,
            )
        ]
        stages = [
            {
                "id": "resume_validation",
                "status": "completed",
                "message": "CV passed factual and visual validation",
            }
        ]
        pack_status = "partial"
        message = cover_failure
        if request.cover_letter is not None and cover_prepared is not None:
            cover_template, cover_content, cover_validation = cover_prepared
            document_ids.append(
                persist_pack_document(
                    db=db,
                    item=request.cover_letter,
                    document_type="cover_letter",
                    template=cover_template,
                    rendered_content=cover_content,
                    validation=cover_validation,
                    job_id=request.job_id,
                    application_id=request.application_id,
                    created_at=now,
                )
            )
            pack_status = "completed"
            message = "Application pack saved atomically"
            stages.append(
                {
                    "id": "cover_letter_validation",
                    "status": "completed",
                    "message": "Cover letter passed factual and visual validation",
                }
            )
        else:
            stages.append(
                {
                    "id": "cover_letter_validation",
                    "status": "failed" if request.cover_letter else "skipped",
                    "message": cover_failure,
                }
            )
        stages.append(
            {
                "id": "saving",
                "status": "completed",
                "message": (
                    "Both documents committed in one transaction"
                    if pack_status == "completed"
                    else "Validated CV saved as an explicit partial pack"
                ),
            }
        )
        job = DocumentPackJobRecord(
            id=request.pack_job_id,
            request_fingerprint=request_fingerprint,
            application_id=request.application_id,
            persistence_mode=request.persistence_mode,
            status=pack_status,
            document_ids=document_ids,
            stages=stages,
            message=message,
            created_at=now,
            updated_at=now,
        )
        db.add(job)
        db.commit()
        return document_pack_payload(job, db)
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
        has_provenance = validate_generation_provenance(
            request.generation_fingerprint,
            request.generation_model,
            request.input_versions,
        )
        if (has_provenance or "template_id" in fields) and (
            "content" not in fields or request.content is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Generation provenance and template require document content",
            )
        if "title" in fields and request.title is not None:
            record.title = request.title.strip()
        if "job_id" in fields:
            record.job_id = request.job_id
        if "content" in fields and request.content is not None:
            current = current_version_record(record)
            if current.content != request.content or has_provenance or "template_id" in fields:
                now = utc_now()
                current_provenance = record.generation_provenance
                if current_provenance and not any(
                    provenance.version == record.current_version
                    for provenance in record.version_generation_provenance
                ):
                    append_version_generation_provenance(
                        record,
                        record.current_version,
                        current_provenance.generation_fingerprint,
                        current_provenance.generation_model,
                        current_provenance.input_versions,
                        now,
                    )
                next_version = record.current_version + 1
                record.versions.append(
                    DocumentVersionRecord(
                        id=str(uuid4()),
                        document_id=record.id,
                        version=next_version,
                        content=request.content,
                        created_at=now,
                    )
                )
                current_file = document_file_record(db, record.id, record.current_version)
                if "template_id" in fields:
                    template_id = request.template_id
                else:
                    template_id = current_file.template_id if current_file else None
                if template_id:
                    template = require_template(db, template_id)
                    if template.type != record.type:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            detail="Document template type does not match document type",
                        )
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
                    if has_provenance:
                        if not request.validation_evidence:
                            raise HTTPException(
                                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                                detail="Validation evidence is required for generated documents",
                            )
                        validation = validate_document_or_422(
                            template_content=template.content,
                            rendered_content=rendered_content,
                            generated_content=request.content,
                            document_type=record.type,
                            evidence=request.validation_evidence,
                        )
                        append_document_validation(
                            record,
                            next_version,
                            validation,
                            now,
                        )
                    db.add(
                        DocumentFileRecord(
                            id=str(uuid4()),
                            document_id=record.id,
                            version=next_version,
                            template_id=template.id,
                            content=rendered_content,
                            created_at=now,
                        )
                    )
                if has_provenance:
                    set_current_generation_provenance(
                        record,
                        request.generation_fingerprint or "",
                        request.generation_model or "",
                        request.input_versions,
                        now,
                    )
                current_provenance = record.generation_provenance
                if current_provenance:
                    append_version_generation_provenance(
                        record,
                        next_version,
                        current_provenance.generation_fingerprint,
                        current_provenance.generation_model,
                        current_provenance.input_versions,
                        now,
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
        now = utc_now()
        next_version = record.current_version + 1
        record.versions.append(
            DocumentVersionRecord(
                id=str(uuid4()),
                document_id=record.id,
                version=next_version,
                content=source.content,
                created_at=now,
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
                    created_at=now,
                )
            )
        source_provenance = next(
            (
                provenance
                for provenance in record.version_generation_provenance
                if provenance.version == source.version
            ),
            None,
        )
        if source_provenance:
            set_current_generation_provenance(
                record,
                source_provenance.generation_fingerprint,
                source_provenance.generation_model,
                source_provenance.input_versions,
                now,
            )
            append_version_generation_provenance(
                record,
                next_version,
                source_provenance.generation_fingerprint,
                source_provenance.generation_model,
                source_provenance.input_versions,
                now,
            )
        else:
            record.generation_provenance = None
        source_validation = next(
            (
                validation
                for validation in record.version_validations
                if validation.version == source.version
            ),
            None,
        )
        if source_validation:
            append_document_validation(
                record,
                next_version,
                {
                    "factual": source_validation.factual_report,
                    "visual": source_validation.visual_report,
                    "diff": source_validation.diff_items,
                },
                now,
            )
        record.current_version = next_version
        record.updated_at = now
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


def validate_generation_provenance(
    generation_fingerprint: str | None,
    generation_model: str | None,
    input_versions: dict[str, object],
) -> bool:
    fields_present = (
        generation_fingerprint is not None,
        bool(generation_model and generation_model.strip()),
        bool(input_versions),
    )
    if any(fields_present) and not all(fields_present):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Generation fingerprint, model, and input versions must be provided together",
        )
    return all(fields_present)


def set_current_generation_provenance(
    record: DocumentRecord,
    generation_fingerprint: str,
    generation_model: str,
    input_versions: dict[str, object],
    created_at: datetime,
) -> None:
    provenance = record.generation_provenance
    if provenance is None:
        provenance = DocumentGenerationProvenanceRecord(document_id=record.id)
        record.generation_provenance = provenance
    provenance.generation_fingerprint = generation_fingerprint
    provenance.generation_model = generation_model.strip()
    provenance.input_versions = input_versions
    provenance.created_at = created_at


def append_version_generation_provenance(
    record: DocumentRecord,
    version: int,
    generation_fingerprint: str,
    generation_model: str,
    input_versions: dict[str, object],
    created_at: datetime,
) -> None:
    record.version_generation_provenance.append(
        DocumentVersionGenerationProvenanceRecord(
            document_id=record.id,
            version=version,
            generation_fingerprint=generation_fingerprint,
            generation_model=generation_model.strip(),
            input_versions=input_versions,
            created_at=created_at,
        )
    )


def validate_document_or_422(
    *,
    template_content: bytes,
    rendered_content: bytes,
    generated_content: str,
    document_type: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    try:
        return validate_generated_document(
            template_content=template_content,
            rendered_content=rendered_content,
            generated_content=generated_content,
            document_type=document_type,
            evidence=evidence,
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


def append_document_validation(
    record: DocumentRecord,
    version: int,
    validation: dict[str, object],
    created_at: datetime,
) -> None:
    record.version_validations.append(
        DocumentVersionValidationRecord(
            document_id=record.id,
            version=version,
            factual_report=validation.get("factual", {}),
            visual_report=validation.get("visual", {}),
            diff_items=validation.get("diff", []),
            created_at=created_at,
        )
    )


def prepare_pack_document(
    db: Session,
    item: DocumentPackItemRequest,
    document_type: str,
) -> tuple[DocumentTemplateRecord, bytes, dict[str, object]]:
    if not item.input_versions:
        raise DocumentValidationError("Generation input versions are required")
    if not item.validation_evidence:
        raise DocumentValidationError("Validation evidence is required")
    template = require_template(db, item.template_id)
    if template.type != document_type:
        raise DocumentValidationError("Document template type does not match pack item type")
    rendered_content = build_document_from_template(
        template_content=template.content,
        content=item.content,
        document_type=document_type,
    )
    validation = validate_generated_document(
        template_content=template.content,
        rendered_content=rendered_content,
        generated_content=item.content,
        document_type=document_type,
        evidence=item.validation_evidence,
    )
    return template, rendered_content, validation


def persist_pack_document(
    *,
    db: Session,
    item: DocumentPackItemRequest,
    document_type: str,
    template: DocumentTemplateRecord,
    rendered_content: bytes,
    validation: dict[str, object],
    job_id: str | None,
    application_id: str,
    created_at: datetime,
) -> str:
    if item.document_id:
        record = require_document(db, item.document_id)
        if record.type != document_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Existing document type does not match pack item type",
            )
        next_version = record.current_version + 1
        record.title = item.title.strip()
        record.job_id = job_id
    else:
        document_id = str(uuid4())
        record = DocumentRecord(
            id=document_id,
            type=document_type,
            title=item.title.strip(),
            job_id=job_id,
            current_version=1,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(record)
        next_version = 1

    record.versions.append(
        DocumentVersionRecord(
            id=str(uuid4()),
            document_id=record.id,
            version=next_version,
            content=item.content,
            created_at=created_at,
        )
    )
    set_current_generation_provenance(
        record,
        item.generation_fingerprint,
        item.generation_model,
        item.input_versions,
        created_at,
    )
    append_version_generation_provenance(
        record,
        next_version,
        item.generation_fingerprint,
        item.generation_model,
        item.input_versions,
        created_at,
    )
    append_document_validation(record, next_version, validation, created_at)
    db.add(
        DocumentFileRecord(
            id=str(uuid4()),
            document_id=record.id,
            version=next_version,
            template_id=template.id,
            content=rendered_content,
            created_at=created_at,
        )
    )
    attach_document_record(db, record, application_id)
    record.current_version = next_version
    record.updated_at = created_at
    return record.id


def document_pack_request_fingerprint(request: DocumentPackRequest) -> str:
    canonical = json.dumps(
        request.model_dump(mode="json", by_alias=True),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def document_pack_payload(job: DocumentPackJobRecord, db: Session) -> DocumentPackPayload:
    documents = [document_payload(require_document(db, document_id)) for document_id in job.document_ids]
    return DocumentPackPayload(
        pack_job_id=job.id,
        status=job.status,
        persistence_mode=job.persistence_mode,
        documents=documents,
        stages=[DocumentPackStagePayload.model_validate(stage) for stage in job.stages],
        message=job.message,
    )


def pack_validation_failed(stage: str, exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "stage": stage,
            "status": "rolled_back",
            "message": str(exc),
        },
    )


def require_document(db: Session, document_id: str) -> DocumentRecord:
    record = db.scalar(
        select(DocumentRecord)
        .where(DocumentRecord.id == document_id)
        .options(
            selectinload(DocumentRecord.versions),
            selectinload(DocumentRecord.attachments),
            selectinload(DocumentRecord.generation_provenance),
            selectinload(DocumentRecord.version_generation_provenance),
            selectinload(DocumentRecord.version_validations),
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
    provenance = record.generation_provenance
    validations_by_version = {
        validation.version: validation for validation in record.version_validations
    }
    return DocumentPayload(
        id=record.id,
        type=record.type,
        title=record.title,
        job_id=record.job_id,
        application_ids=[item.application_id for item in record.attachments],
        current_version=record.current_version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        generation_fingerprint=provenance.generation_fingerprint if provenance else None,
        generation_model=provenance.generation_model if provenance else None,
        input_versions=provenance.input_versions if provenance else {},
        versions=[
            DocumentVersionPayload(
                id=version.id,
                version=version.version,
                content=version.content,
                created_at=version.created_at,
                factual_validation=(
                    validations_by_version[version.version].factual_report
                    if version.version in validations_by_version
                    else {}
                ),
                visual_validation=(
                    validations_by_version[version.version].visual_report
                    if version.version in validations_by_version
                    else {}
                ),
                diff=(
                    validations_by_version[version.version].diff_items
                    if version.version in validations_by_version
                    else []
                ),
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
