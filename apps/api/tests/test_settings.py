from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.settings import format_env_value, mask_secret, upsert_env_value
from app.core.settings import Settings, get_settings
from app.main import app


def test_mask_secret_keeps_only_edges() -> None:
    assert mask_secret("abcd1234wxyz") == "abcd****wxyz"
    assert mask_secret("short") == "****"
    assert mask_secret("") == ""


def test_format_env_value_quotes_values_that_need_it() -> None:
    assert format_env_value("plain_key-123") == "plain_key-123"
    assert format_env_value("key with spaces") == '"key with spaces"'
    assert format_env_value('key"with\\chars') == '"key\\"with\\\\chars"'


def test_upsert_env_value_preserves_other_lines(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "DATABASE_URL=postgresql://example\n"
        "BRIGHTDATA_API_KEY=old-key\n"
        "# BRIGHTDATA_API_KEY=commented\n",
        encoding="utf-8",
    )

    upsert_env_value(env_path, "BRIGHTDATA_API_KEY", "new-key")

    assert env_path.read_text(encoding="utf-8") == (
        "DATABASE_URL=postgresql://example\n"
        "BRIGHTDATA_API_KEY=new-key\n"
        "# BRIGHTDATA_API_KEY=commented\n"
    )


def test_get_brightdata_api_key_returns_full_key(monkeypatch) -> None:
    monkeypatch.setenv("BRIGHTDATA_API_KEY", "full-secret-key")
    get_settings.cache_clear()
    client = TestClient(app)

    try:
        response = client.get("/settings/brightdata-key")
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json() == {"brightdata_api_key": "full-secret-key"}


def test_ai_backend_mode_accepts_only_supported_transports() -> None:
    settings = Settings(
        ai_backend_mode="openai_api",
        openai_api_key="test-key",
        openai_api_base_url="https://api.openai.test/v1",
        openai_api_model="gpt-test",
    )

    assert settings.ai_backend_mode == "openai_api"
    assert settings.openai_api_key == "test-key"
    assert Settings().ai_backend_mode == "openclaw_codex"

    with pytest.raises(ValidationError):
        Settings(ai_backend_mode="unsupported")
