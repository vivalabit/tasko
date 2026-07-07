from typing import Any, Literal

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


class AiMatchJobStatus(BaseModel):
    run_id: str = Field(default="", alias="runId")
    status: Literal["idle", "queued", "running", "completed", "failed"] = "idle"
    total: int = 0
    processed: int = 0
    updated_jobs: list[StoredJobPayload] = Field(default_factory=list, alias="updatedJobs")
    error: str | None = None

    model_config = {"populate_by_name": True}
