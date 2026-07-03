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
    name: str = Field(min_length=1, max_length=120)
    current_role: str = Field(min_length=1, max_length=160)
    desired_role: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=160)
    work_format: str = Field(min_length=1, max_length=120)
    headline: str = Field(min_length=1, max_length=600)
    linkedin: str = Field(default="", max_length=240)
    github: str = Field(default="", max_length=240)
    portfolio: str = Field(default="", max_length=240)
    personal_site: str = Field(default="", max_length=240)
