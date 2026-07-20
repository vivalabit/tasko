from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://tasko:tasko@localhost:5432/tasko"
    redis_url: str = "redis://localhost:6379/0"
    openclaw_resume_import_enabled: bool = True
    openclaw_command: str = "openclaw"
    openclaw_agent_id: str = "tasko-assistant"
    openclaw_resume_import_thinking: str = "high"
    openclaw_resume_import_timeout_seconds: int = 120
    openclaw_ai_match_enabled: bool = True
    openclaw_ai_match_model: str = "openai/gpt-5.6-terra"
    openclaw_ai_match_thinking: str = "low"
    openclaw_ai_match_timeout_seconds: int = 120
    openclaw_ai_match_max_jobs: int = 3
    openclaw_assistant_enabled: bool = True
    openclaw_assistant_agent_id: str = "tasko-assistant"
    openclaw_assistant_model: str = "openai/gpt-5.6-terra"
    ai_provider_name: str = "OpenAI"
    ai_consent_version: str = "2026-07-18.v2"
    storage_cleanup_interval_seconds: int = Field(default=300, ge=1, le=86_400)
    openclaw_assistant_thinking: str = "off"
    openclaw_assistant_timeout_seconds: int = Field(default=120, ge=10, le=600)
    openclaw_assistant_max_attempts: int = Field(default=2, ge=1, le=4)
    openclaw_assistant_retry_backoff_seconds: float = Field(default=0.8, ge=0, le=10)
    openclaw_assistant_max_prompt_chars: int = Field(default=32_000, ge=4_000, le=200_000)
    openclaw_assistant_max_user_message_chars: int = Field(default=6_000, ge=200, le=12_000)
    openclaw_assistant_max_history_messages: int = Field(default=12, ge=0, le=100)
    openclaw_assistant_max_history_chars: int = Field(default=8_000, ge=0, le=100_000)
    brightdata_api_key: str | None = None
    brightdata_api_url: str = "https://api.brightdata.com/datasets/v3"
    brightdata_linkedin_jobs_dataset_id: str = "gd_lpfll7v5hcqtkxl6l"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    cors_origin_regex: str = (
        r"^http://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}):300[01]$"
    )

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
