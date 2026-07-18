import asyncio

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import main as main_module
from app.core.database import Base
from app.core.migrations import get_alembic_config, upgrade_database


def test_baseline_migration_matches_current_schema(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'baseline.sqlite'}"

    upgrade_database(database_url)

    engine = create_engine(database_url)
    try:
        table_names = set(inspect(engine).get_table_names())
        assert table_names == {*Base.metadata.tables, "alembic_version"}

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "20260718_0002"
    finally:
        engine.dispose()

    command.check(get_alembic_config(database_url))


def test_upgrade_database_can_run_again_at_head(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'repeat.sqlite'}"

    upgrade_database(database_url)
    upgrade_database(database_url)


def test_lifespan_propagates_database_initialization_error(monkeypatch) -> None:
    def fail_upgrade() -> None:
        raise SQLAlchemyError("database initialization failed")

    monkeypatch.setattr(main_module, "upgrade_database", fail_upgrade)

    async def start_application() -> None:
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(SQLAlchemyError, match="database initialization failed"):
        asyncio.run(start_application())
