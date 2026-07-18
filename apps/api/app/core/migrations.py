from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.settings import get_settings

API_ROOT = Path(__file__).resolve().parents[2]


def get_alembic_config(database_url: str | None = None) -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    config.attributes["database_url"] = database_url or get_settings().database_url
    return config


def upgrade_database(database_url: str | None = None) -> None:
    command.upgrade(get_alembic_config(database_url), "head")
