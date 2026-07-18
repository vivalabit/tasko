import asyncio

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app import main as main_module
from app.core.database import Base
from app.core.migrations import (
    LegacyDatabaseMismatchError,
    get_alembic_config,
    upgrade_database,
)


def test_baseline_migration_matches_current_schema(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'baseline.sqlite'}"

    upgrade_database(database_url)

    engine = create_engine(database_url)
    try:
        table_names = set(inspect(engine).get_table_names())
        assert table_names == {*Base.metadata.tables, "alembic_version"}
        template_constraints = inspect(engine).get_unique_constraints(
            "document_templates"
        )
        assert {
            tuple(constraint["column_names"])
            for constraint in template_constraints
        } == {("type", "content_sha256")}
        pack_indexes = inspect(engine).get_indexes("document_pack_jobs")
        assert any(index["column_names"] == ["expires_at"] for index in pack_indexes)

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "20260718_0003"
    finally:
        engine.dispose()

    command.check(get_alembic_config(database_url))


def test_upgrade_database_can_run_again_at_head(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'repeat.sqlite'}"

    upgrade_database(database_url)
    upgrade_database(database_url)


def test_upgrade_database_bootstraps_legacy_baseline(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy.sqlite'}"
    config = get_alembic_config(database_url)
    command.upgrade(config, "20260718_0001")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE alembic_version"))
    finally:
        engine.dispose()

    upgrade_database(database_url)

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "20260718_0003"
    finally:
        engine.dispose()
    command.check(get_alembic_config(database_url))


def test_upgrade_database_rejects_unknown_unversioned_schema(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'unknown.sqlite'}"
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)"))
    finally:
        engine.dispose()

    with pytest.raises(
        LegacyDatabaseMismatchError,
        match="unexpected tables: unrelated",
    ):
        upgrade_database(database_url)

    engine = create_engine(database_url)
    try:
        assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_upgrade_database_rolls_back_mismatched_legacy_schema(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'mismatched-legacy.sqlite'}"
    command.upgrade(get_alembic_config(database_url), "20260718_0001")
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE alembic_version"))
            connection.execute(text("ALTER TABLE profiles DROP COLUMN data"))
    finally:
        engine.dispose()

    with pytest.raises(
        LegacyDatabaseMismatchError,
        match="column mismatch: profiles",
    ):
        upgrade_database(database_url)

    engine = create_engine(database_url)
    try:
        assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_lifespan_propagates_database_initialization_error(monkeypatch) -> None:
    def fail_upgrade() -> None:
        raise SQLAlchemyError("database initialization failed")

    monkeypatch.setattr(main_module, "upgrade_database", fail_upgrade)

    async def start_application() -> None:
        async with main_module.lifespan(main_module.app):
            pass

    with pytest.raises(SQLAlchemyError, match="database initialization failed"):
        asyncio.run(start_application())
