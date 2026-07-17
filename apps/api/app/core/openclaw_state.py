"""Prepare a container-local copy of OpenClaw's SQLite state database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


DEFAULT_SOURCE_DB = Path("/root/.openclaw-shared-state/openclaw.sqlite")
DEFAULT_TARGET_DB = Path("/root/.openclaw/state/openclaw.sqlite")
PLUGIN_STATE_INDEX = "idx_plugin_state_listing"


def prepare_openclaw_state(
    source_db: Path = DEFAULT_SOURCE_DB,
    target_db: Path = DEFAULT_TARGET_DB,
) -> str:
    """Seed and repair the container-local OpenClaw state database."""
    target_db.parent.mkdir(parents=True, exist_ok=True)

    if not target_db.exists():
        if not source_db.is_file():
            raise RuntimeError(
                f"OpenClaw state source is unavailable: {source_db}"
            )
        _backup_database(source_db, target_db)

    with sqlite3.connect(target_db) as connection:
        connection.execute(f"REINDEX {PLUGIN_STATE_INDEX}")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        result = str(integrity[0]) if integrity else "missing integrity result"
        if result != "ok":
            raise RuntimeError(f"OpenClaw state database is malformed: {result}")

    os.chmod(target_db, 0o600)
    return result


def _backup_database(source_db: Path, target_db: Path) -> None:
    # The shared macOS database is mounted read-only and can have WAL sidecars.
    # immutable=1 prevents SQLite from trying to create or update a SHM file.
    source_uri = f"file:{source_db}?mode=ro&immutable=1"
    try:
        with sqlite3.connect(source_uri, uri=True) as source:
            with sqlite3.connect(target_db) as target:
                source.backup(target)
    except Exception:
        target_db.unlink(missing_ok=True)
        raise


def main() -> None:
    result = prepare_openclaw_state()
    print(f"OpenClaw container state integrity: {result}", flush=True)


if __name__ == "__main__":
    main()
