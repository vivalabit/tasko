from pathlib import Path

from app.api.settings import format_env_value, mask_secret, upsert_env_value


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
