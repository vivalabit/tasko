import sqlite3
from pathlib import Path

from app.core.openclaw_state import prepare_openclaw_state


def create_plugin_state_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE plugin_state (plugin_id TEXT PRIMARY KEY, enabled INTEGER)"
        )
        connection.execute(
            "CREATE INDEX idx_plugin_state_listing ON plugin_state (enabled, plugin_id)"
        )
        connection.execute("INSERT INTO plugin_state VALUES ('codex', 1)")


def test_prepare_openclaw_state_seeds_container_database(tmp_path: Path) -> None:
    source = tmp_path / "shared" / "openclaw.sqlite"
    target = tmp_path / "container" / "openclaw.sqlite"
    source.parent.mkdir()
    create_plugin_state_database(source)

    assert prepare_openclaw_state(source, target) == "ok"

    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT * FROM plugin_state").fetchall() == [
            ("codex", 1)
        ]


def test_prepare_openclaw_state_preserves_existing_container_database(
    tmp_path: Path,
) -> None:
    source = tmp_path / "shared.sqlite"
    target = tmp_path / "container.sqlite"
    create_plugin_state_database(source)
    create_plugin_state_database(target)
    with sqlite3.connect(target) as connection:
        connection.execute("INSERT INTO plugin_state VALUES ('tasko-only', 1)")

    assert prepare_openclaw_state(source, target) == "ok"

    with sqlite3.connect(target) as connection:
        assert connection.execute(
            "SELECT plugin_id FROM plugin_state ORDER BY plugin_id"
        ).fetchall() == [("codex",), ("tasko-only",)]
