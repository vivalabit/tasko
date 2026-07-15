from typing import Any, Literal

from pydantic import BaseModel, Field


class AssistantAiMatchContext(BaseModel):
    reasons: list[str] = Field(default_factory=list, max_length=8)
    gaps: list[str] = Field(default_factory=list, max_length=8)


class AssistantJobContext(BaseModel):
    id: str = Field(default="", max_length=160)
    title: str = Field(default="", max_length=240)
    company: str = Field(default="", max_length=240)
    location: str = Field(default="", max_length=240)
    type: str = Field(default="", max_length=120)
    match: int = Field(default=0, ge=0, le=100)
    overview: str = Field(default="", max_length=12_000)
    responsibilities: list[str] = Field(default_factory=list, max_length=40)
    requirements: list[str] = Field(default_factory=list, max_length=40)
    skills: list[str] = Field(default_factory=list, max_length=80)
    ai_match: AssistantAiMatchContext | None = Field(default=None, alias="aiMatch")

    model_config = {"populate_by_name": True}


class AssistantApplicationContext(BaseModel):
    id: str = Field(default="", max_length=160)
    status: str = Field(default="", max_length=80)
    next_step: str = Field(default="", max_length=500, alias="nextStep")
    notes: str = Field(default="", max_length=12_000)
    job: AssistantJobContext

    model_config = {"populate_by_name": True}


class AssistantChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=160, alias="threadId")
    message: str = Field(min_length=1, max_length=12_000)
    context_kind: Literal["profile", "job", "application"] = Field(alias="contextKind")
    context_id: str = Field(default="", max_length=160, alias="contextId")
    job: AssistantJobContext | None = None
    application: AssistantApplicationContext | None = None

    model_config = {"populate_by_name": True}


class AssistantStreamRequest(AssistantChatRequest):
    request_id: str = Field(min_length=1, max_length=160, alias="requestId")
    offset: int = Field(default=0, ge=0, le=1_000_000)


class AssistantChatResponse(BaseModel):
    message: str
    source: Literal["openclaw"] = "openclaw"
    metadata: dict[str, Any] = Field(default_factory=dict)
