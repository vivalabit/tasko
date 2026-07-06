from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, String
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
