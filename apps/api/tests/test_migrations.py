import asyncio
from datetime import UTC, datetime, timedelta

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
        } == {("owner_id", "type", "content_sha256")}
        pack_indexes = inspect(engine).get_indexes("document_pack_jobs")
        assert any(index["column_names"] == ["expires_at"] for index in pack_indexes)
        pack_foreign_keys = inspect(engine).get_foreign_keys("document_pack_jobs")
        assert [
            (
                foreign_key["constrained_columns"],
                foreign_key["referred_table"],
                foreign_key["referred_columns"],
                foreign_key["options"].get("ondelete"),
            )
            for foreign_key in pack_foreign_keys
        ] == [(["application_id"], "stored_applications", ["id"], "CASCADE")]
        artifact_foreign_keys = inspect(engine).get_foreign_keys(
            "document_validation_artifacts"
        )
        assert {
            (
                tuple(foreign_key["constrained_columns"]),
                foreign_key["referred_table"],
                tuple(foreign_key["referred_columns"]),
                foreign_key["options"].get("ondelete"),
            )
            for foreign_key in artifact_foreign_keys
        } == {
            (("application_id",), "stored_applications", ("id",), "CASCADE"),
            (("template_id",), "document_templates", ("id",), "CASCADE"),
        }
        artifact_indexes = inspect(engine).get_indexes("document_validation_artifacts")
        assert {tuple(index["column_names"]) for index in artifact_indexes} >= {
            ("expires_at",),
            ("template_id",),
        }
        owner_tables = {
            "stored_applications",
            "stored_application_events",
            "candidate_confirmations",
            "documents",
            "document_pack_jobs",
            "document_validation_artifacts",
            "document_templates",
            "workspace_source_documents",
            "conversations",
            "applied_assistant_actions",
            "job_matches",
            "candidate_match_snapshots",
        }
        for table_name in owner_tables:
            owner_column = next(
                column
                for column in inspect(engine).get_columns(table_name)
                if column["name"] == "owner_id"
            )
            assert owner_column["nullable"] is False
            assert any(
                index["column_names"] == ["owner_id"]
                for index in inspect(engine).get_indexes(table_name)
            )

        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "20260719_0007"
    finally:
        engine.dispose()

    command.check(get_alembic_config(database_url))


def test_upgrade_database_can_run_again_at_head(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'repeat.sqlite'}"

    upgrade_database(database_url)
    upgrade_database(database_url)


def test_storage_foreign_key_migration_removes_existing_orphans(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'storage-orphans.sqlite'}"
    config = get_alembic_config(database_url)
    command.upgrade(config, "20260719_0004")
    now = datetime.now(UTC)

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO stored_applications (id, data) "
                    "VALUES ('legacy-application', '{}')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO document_templates "
                    "(id, type, name, file_name, content_type, content, extracted_text, "
                    "created_at, updated_at, content_sha256) "
                    "VALUES ('legacy-template', 'tailored_resume', 'Legacy', 'legacy.docx', "
                    "'application/vnd.openxmlformats-officedocument.wordprocessingml.document', "
                    ":content, '', :created_at, :updated_at, :content_sha256)"
                ),
                {
                    "content": b"legacy-template",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "content_sha256": "f" * 64,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO document_pack_jobs "
                    "(id, request_fingerprint, application_id, persistence_mode, status, "
                    "document_ids, stages, message, created_at, updated_at, expires_at) "
                    "VALUES (:id, :fingerprint, :application_id, 'atomic', 'completed', "
                    "'[]', '[]', '', :created_at, :updated_at, :expires_at)"
                ),
                {
                    "id": "orphan-pack",
                    "fingerprint": "a" * 64,
                    "application_id": "missing-application",
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                    "expires_at": (now + timedelta(days=1)).isoformat(),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO document_validation_artifacts "
                    "(id, application_id, document_type, template_id, template_hash, "
                    "result_hash, evidence_hash, rendered_hash, rendered_content, "
                    "validation_report, consumed_at, expires_at, created_at) "
                    "VALUES (:id, :application_id, 'tailored_resume', :template_id, "
                    ":template_hash, :result_hash, :evidence_hash, :rendered_hash, "
                    ":rendered_content, '{}', NULL, :expires_at, :created_at)"
                ),
                {
                    "id": "orphan-artifact",
                    "application_id": "missing-application",
                    "template_id": "missing-template",
                    "template_hash": "b" * 64,
                    "result_hash": "c" * 64,
                    "evidence_hash": "d" * 64,
                    "rendered_hash": "e" * 64,
                    "rendered_content": b"rendered",
                    "expires_at": (now + timedelta(minutes=30)).isoformat(),
                    "created_at": now.isoformat(),
                },
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT COUNT(*) FROM document_pack_jobs")
            ).scalar_one() == 0
            assert connection.execute(
                text("SELECT COUNT(*) FROM document_validation_artifacts")
            ).scalar_one() == 0
            assert connection.execute(
                text(
                    "SELECT owner_id FROM stored_applications "
                    "WHERE id = 'legacy-application'"
                )
            ).scalar_one() == "local-owner"
            assert connection.execute(
                text(
                    "SELECT owner_id FROM document_templates "
                    "WHERE id = 'legacy-template'"
                )
            ).scalar_one() == "local-owner"
    finally:
        engine.dispose()


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
        assert revision == "20260719_0007"
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


def test_lifespan_starts_and_stops_scheduled_expiration_cleanup(monkeypatch) -> None:
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def scheduled_cleanup(interval_seconds: int) -> None:
        assert interval_seconds == main_module.settings.storage_cleanup_interval_seconds
        started.set()
        try:
            await asyncio.Future()
        finally:
            stopped.set()

    monkeypatch.setattr(main_module, "upgrade_database", lambda: None)
    monkeypatch.setattr(main_module, "run_expiration_cleanup", scheduled_cleanup)

    async def start_application() -> None:
        async with main_module.lifespan(main_module.app):
            await asyncio.wait_for(started.wait(), timeout=1)
        await asyncio.wait_for(stopped.wait(), timeout=1)

    asyncio.run(start_application())
