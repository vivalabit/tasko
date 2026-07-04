from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProfileRecord(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class ProfilePayload(BaseModel):
    avatar_url: str = Field(default="/avatars/default-pug.png", max_length=1_500_000)
    name: str = Field(default="", max_length=120)
    current_role: str = Field(default="", max_length=160)
    desired_role: str = Field(default="", max_length=160)
    location: str = Field(default="", max_length=160)
    work_format: str = Field(default="", max_length=120)
    headline: str = Field(default="", max_length=600)
    linkedin: str = Field(default="", max_length=240)
    github: str = Field(default="", max_length=240)
    portfolio: str = Field(default="", max_length=240)
    personal_site: str = Field(default="", max_length=240)
    experience: str = Field(default="", max_length=4000)
    skills: str = Field(default="", max_length=2000)
    education: str = Field(default="", max_length=2000)
    job_preferences: str = Field(default="", max_length=2000)
    dealbreakers: str = Field(default="", max_length=2000)
    additional_notes: str = Field(default="", max_length=2000)
    resume_file_name: str = Field(default="", max_length=240)
    resume_file_size: str = Field(default="", max_length=40)
    resume_updated_at: str = Field(default="", max_length=80)
    resume_data_url: str = Field(default="", max_length=10_000_000)
