from collections.abc import AsyncGenerator
from contextvars import ContextVar
from dataclasses import dataclass
import re
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.settings import Settings, get_settings

DEFAULT_OWNER_ID = "local-owner"
OWNER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,159}$")

current_owner_id: ContextVar[str | None] = ContextVar(
    "rufina_current_owner_id",
    default=None,
)


def get_bound_owner_id() -> str:
    return current_owner_id.get() or DEFAULT_OWNER_ID


@dataclass(frozen=True)
class RequestIdentity:
    owner_id: str


def get_request_identity(
    owner_id: Annotated[
        str | None,
        Header(alias="X-Rufina-Owner-Id"),
    ] = None,
    legacy_owner_id: Annotated[
        str | None,
        Header(alias="X-Tasko-Owner-Id"),
    ] = None,
    settings: Settings = Depends(get_settings),
) -> RequestIdentity:
    normalized = (owner_id or legacy_owner_id or "").strip()
    if owner_id and legacy_owner_id and owner_id.strip() != legacy_owner_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflicting authenticated owner identities",
        )
    if not normalized and settings.app_env == "local":
        normalized = DEFAULT_OWNER_ID
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated owner identity is required",
        )
    if not OWNER_ID_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated owner identity is invalid",
        )
    return RequestIdentity(owner_id=normalized)


async def bind_request_identity(
    identity: RequestIdentity = Depends(get_request_identity),
) -> AsyncGenerator[None, None]:
    token = current_owner_id.set(identity.owner_id)
    try:
        yield
    finally:
        current_owner_id.reset(token)
