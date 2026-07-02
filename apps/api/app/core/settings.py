from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://tasko:tasko@localhost:5432/tasko"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str | None = None
    brightdata_api_key: str | None = None
    brightdata_api_url: str = "https://api.brightdata.com/datasets/v3"
    brightdata_linkedin_jobs_dataset_id: str = "gd_lpfll7v5hcqtkxl6l"
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
