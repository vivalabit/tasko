from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StoredJobRecord(Base):
    __tablename__ = "stored_jobs"

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class StoredJobPayload(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    data: dict[str, Any]


class StoredJobsRequest(BaseModel):
    jobs: list[StoredJobPayload] = Field(default_factory=list)
