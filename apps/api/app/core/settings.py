from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://tasko:tasko@localhost:5432/tasko"
    redis_url: str = "redis://localhost:6379/0"
    openclaw_resume_import_enabled: bool = True
    openclaw_command: str = "openclaw"
    openclaw_agent_id: str = "main"
    openclaw_resume_import_thinking: str = "high"
    openclaw_resume_import_timeout_seconds: int = 120
    openclaw_ai_match_enabled: bool = True
    openclaw_ai_match_thinking: str = "low"
    openclaw_ai_match_timeout_seconds: int = 90
    openclaw_ai_match_max_jobs: int = 20
    brightdata_api_key: str | None = None
    brightdata_api_url: str = "https://api.brightdata.com/datasets/v3"
    brightdata_linkedin_jobs_dataset_id: str = "gd_lpfll7v5hcqtkxl6l"
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_origin_regex: str = (
        r"^http://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}):3000$"
    )

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
