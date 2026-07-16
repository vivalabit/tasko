from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
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


class DocumentVersionPayload(BaseModel):
    id: str
    version: int
    content: str
    created_at: datetime = Field(alias="createdAt")

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
    versions: list[DocumentVersionPayload]

    model_config = {"populate_by_name": True}


class DocumentCreateRequest(BaseModel):
    type: DocumentType
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=200_000)
    job_id: str | None = Field(default=None, max_length=160, alias="jobId")
    application_id: str | None = Field(default=None, max_length=160, alias="applicationId")
    template_id: str | None = Field(default=None, max_length=36, alias="templateId")

    model_config = {"populate_by_name": True}


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    content: str | None = Field(default=None, min_length=1, max_length=200_000)
    job_id: str | None = Field(default=None, max_length=160, alias="jobId")

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
