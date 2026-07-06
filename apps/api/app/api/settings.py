from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.settings import REPO_ROOT, get_settings

router = APIRouter()

BRIGHTDATA_API_KEY_ENV = "BRIGHTDATA_API_KEY"


class AppSettingsResponse(BaseModel):
    has_brightdata_api_key: bool
    brightdata_api_key_preview: str = ""


class BrightDataApiKeyResponse(BaseModel):
    brightdata_api_key: str = ""


class AppSettingsUpdateRequest(BaseModel):
    brightdata_api_key: str = Field(default="", max_length=4096)


def mask_secret(value: str | None) -> str:
    if not value:
        return ""

    if len(value) <= 8:
        return "****"

    return f"{value[:4]}****{value[-4:]}"


def format_env_value(value: str) -> str:
    if not value:
        return ""

    if all(char.isalnum() or char in "-_." for char in value):
        return value

    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def upsert_env_value(env_path: Path, key: str, value: str) -> None:
    next_line = f"{key}={format_env_value(value)}"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated = False
    next_lines: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if not stripped.startswith("#") and stripped.split("=", 1)[0].strip() == key:
            next_lines.append(next_line)
            updated = True
        else:
            next_lines.append(line)

    if not updated:
        next_lines.append(next_line)

    env_path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")


def build_settings_response() -> AppSettingsResponse:
    settings = get_settings()
    brightdata_api_key = settings.brightdata_api_key or ""

    return AppSettingsResponse(
        has_brightdata_api_key=bool(brightdata_api_key.strip()),
        brightdata_api_key_preview=mask_secret(brightdata_api_key.strip()),
    )


@router.get("", response_model=AppSettingsResponse)
def get_app_settings() -> AppSettingsResponse:
    return build_settings_response()


@router.get("/brightdata-key", response_model=BrightDataApiKeyResponse)
def get_brightdata_api_key() -> BrightDataApiKeyResponse:
    settings = get_settings()
    return BrightDataApiKeyResponse(brightdata_api_key=(settings.brightdata_api_key or "").strip())


@router.put("", response_model=AppSettingsResponse)
def update_app_settings(payload: AppSettingsUpdateRequest) -> AppSettingsResponse:
    brightdata_api_key = payload.brightdata_api_key.strip()

    try:
        upsert_env_value(REPO_ROOT / ".env", BRIGHTDATA_API_KEY_ENV, brightdata_api_key)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Settings file is unavailable",
        ) from exc

    get_settings.cache_clear()
    return build_settings_response()
