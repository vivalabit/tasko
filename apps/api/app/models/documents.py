from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )
    versions: Mapped[list["DocumentVersionRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersionRecord.version",
    )
    attachments: Mapped[list["DocumentAttachmentRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
    generation_provenance: Mapped["DocumentGenerationProvenanceRecord | None"] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )
    version_generation_provenance: Mapped[
        list["DocumentVersionGenerationProvenanceRecord"]
    ] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersionGenerationProvenanceRecord.version",
    )
    version_validations: Mapped[list["DocumentVersionValidationRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersionValidationRecord.version",
    )


class DocumentVersionRecord(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_versions_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentRecord] = relationship(back_populates="versions")


class DocumentAttachmentRecord(Base):
    __tablename__ = "document_attachments"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "application_id",
            name="uq_document_attachments_application",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentRecord] = relationship(back_populates="attachments")


class DocumentGenerationProvenanceRecord(Base):
    __tablename__ = "document_generation_provenance"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    generation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generation_model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentRecord] = relationship(back_populates="generation_provenance")


class DocumentVersionGenerationProvenanceRecord(Base):
    __tablename__ = "document_version_generation_provenance"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    generation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    generation_model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentRecord] = relationship(
        back_populates="version_generation_provenance"
    )


class DocumentVersionValidationRecord(Base):
    __tablename__ = "document_version_validations"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    factual_report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    visual_report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    diff_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    document: Mapped[DocumentRecord] = relationship(back_populates="version_validations")


class DocumentPackJobRecord(Base):
    __tablename__ = "document_pack_jobs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    application_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    persistence_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    stages: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class DocumentTemplateRecord(Base):
    __tablename__ = "document_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    file_name: Mapped[str] = mapped_column(String(240), nullable=False)
    content_type: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class DocumentFileRecord(Base):
    __tablename__ = "document_files"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_files_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    template_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


DocumentType = Literal["cover_letter", "tailored_resume"]
DocumentPackPersistenceMode = Literal["atomic", "partial"]


class DocumentVersionPayload(BaseModel):
    id: str
    version: int
    content: str
    created_at: datetime = Field(alias="createdAt")
    factual_validation: dict[str, Any] = Field(
        default_factory=dict,
        alias="factualValidation",
    )
    visual_validation: dict[str, Any] = Field(
        default_factory=dict,
        alias="visualValidation",
    )
    diff: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DocumentPayload(BaseModel):
    id: str
    type: DocumentType
    title: str
    job_id: str | None = Field(default=None, alias="jobId")
    application_ids: list[str] = Field(default_factory=list, alias="applicationIds")
    current_version: int = Field(alias="currentVersion")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    generation_fingerprint: str | None = Field(default=None, alias="generationFingerprint")
    generation_model: str | None = Field(default=None, alias="generationModel")
    input_versions: dict[str, Any] = Field(default_factory=dict, alias="inputVersions")
    versions: list[DocumentVersionPayload]

    model_config = {"populate_by_name": True}


class DocumentCreateRequest(BaseModel):
    type: DocumentType
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=200_000)
    job_id: str | None = Field(default=None, max_length=160, alias="jobId")
    application_id: str | None = Field(default=None, max_length=160, alias="applicationId")
    template_id: str | None = Field(default=None, max_length=36, alias="templateId")
    generation_fingerprint: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        alias="generationFingerprint",
    )
    generation_model: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        alias="generationModel",
    )
    input_versions: dict[str, Any] = Field(default_factory=dict, alias="inputVersions")
    validation_evidence: dict[str, Any] = Field(
        default_factory=dict,
        alias="validationEvidence",
    )

    model_config = {"populate_by_name": True}


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    content: str | None = Field(default=None, min_length=1, max_length=200_000)
    job_id: str | None = Field(default=None, max_length=160, alias="jobId")
    template_id: str | None = Field(default=None, max_length=36, alias="templateId")
    generation_fingerprint: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        alias="generationFingerprint",
    )
    generation_model: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        alias="generationModel",
    )
    input_versions: dict[str, Any] = Field(default_factory=dict, alias="inputVersions")
    validation_evidence: dict[str, Any] = Field(
        default_factory=dict,
        alias="validationEvidence",
    )

    model_config = {"populate_by_name": True}


class DocumentPackItemRequest(BaseModel):
    document_id: str | None = Field(default=None, max_length=36, alias="documentId")
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=200_000)
    template_id: str = Field(min_length=1, max_length=36, alias="templateId")
    generation_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
        alias="generationFingerprint",
    )
    generation_model: str = Field(
        min_length=1,
        max_length=160,
        alias="generationModel",
    )
    input_versions: dict[str, Any] = Field(alias="inputVersions")
    validation_evidence: dict[str, Any] = Field(alias="validationEvidence")

    model_config = {"populate_by_name": True}


class DocumentPackRequest(BaseModel):
    pack_job_id: str = Field(min_length=1, max_length=80, alias="packJobId")
    job_id: str | None = Field(default=None, max_length=160, alias="jobId")
    application_id: str = Field(min_length=1, max_length=160, alias="applicationId")
    persistence_mode: DocumentPackPersistenceMode = Field(
        default="atomic",
        alias="persistenceMode",
    )
    resume: DocumentPackItemRequest
    cover_letter: DocumentPackItemRequest | None = Field(
        default=None,
        alias="coverLetter",
    )
    partial_reason: str | None = Field(default=None, max_length=500, alias="partialReason")

    model_config = {"populate_by_name": True}


class DocumentPackValidationPayload(BaseModel):
    status: Literal["passed"] = "passed"
    validation: dict[str, Any]


class DocumentPackStagePayload(BaseModel):
    id: Literal["resume_validation", "cover_letter_validation", "saving"]
    status: Literal["completed", "failed", "skipped"]
    message: str = ""


class DocumentPackPayload(BaseModel):
    pack_job_id: str = Field(alias="packJobId")
    status: Literal["completed", "partial"]
    persistence_mode: DocumentPackPersistenceMode = Field(alias="persistenceMode")
    documents: list[DocumentPayload]
    stages: list[DocumentPackStagePayload]
    message: str = ""

    model_config = {"populate_by_name": True}


class DocumentAttachRequest(BaseModel):
    application_id: str = Field(min_length=1, max_length=160, alias="applicationId")

    model_config = {"populate_by_name": True}


class DocumentRestoreRequest(BaseModel):
    version: int = Field(ge=1)


class DocumentTemplateCreateRequest(BaseModel):
    type: DocumentType
    name: str = Field(min_length=1, max_length=240)
    file_name: str = Field(min_length=1, max_length=240, alias="fileName")
    data_url: str = Field(min_length=1, max_length=15_000_000, alias="dataUrl")

    model_config = {"populate_by_name": True}


class DocumentTemplatePayload(BaseModel):
    id: str
    type: DocumentType
    name: str
    file_name: str = Field(alias="fileName")
    extracted_text: str = Field(alias="extractedText")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
