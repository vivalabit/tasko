from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StoredApplicationRecord(Base):
    __tablename__ = "stored_applications"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class StoredApplicationEventRecord(Base):
    __tablename__ = "stored_application_events"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    application_id: Mapped[str] = mapped_column(String(160), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class CandidateConfirmationRecord(Base):
    __tablename__ = "candidate_confirmations"

    application_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    requirement: Mapped[str] = mapped_column(String(500), nullable=False)
    response: Mapped[str] = mapped_column(String(16), nullable=False)
    example_text: Mapped[str] = mapped_column(String(1500), nullable=False, default="")
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StoredApplicationPayload(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    data: dict[str, Any]


class StoredApplicationsRequest(BaseModel):
    applications: list[StoredApplicationPayload] = Field(default_factory=list)


class StoredApplicationEventPayload(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    application_id: str = Field(min_length=1, max_length=160)
    data: dict[str, Any]


class StoredApplicationEventsRequest(BaseModel):
    events: list[StoredApplicationEventPayload] = Field(default_factory=list)


class CandidateConfirmationInput(BaseModel):
    question_id: str = Field(min_length=1, max_length=160, alias="questionId")
    requirement: str = Field(min_length=1, max_length=500)
    response: Literal["yes", "no", "partial"]
    example_text: str = Field(default="", max_length=1500, alias="exampleText")
    blocking: bool = False

    model_config = {"populate_by_name": True}


class CandidateConfirmationsRequest(BaseModel):
    confirmations: list[CandidateConfirmationInput] = Field(default_factory=list, max_length=20)
    required_question_ids: list[str] = Field(
        max_length=20,
        alias="requiredQuestionIds",
    )

    model_config = {"populate_by_name": True}


class CandidateConfirmationPayload(CandidateConfirmationInput):
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}
