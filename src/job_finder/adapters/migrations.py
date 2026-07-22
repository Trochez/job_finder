"""SQLite database migration orchestration and connection helpers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .repositories._query_helpers import fetchall_rows, read_required_text


@dataclass(frozen=True, slots=True)
class SqliteMigration:
    """A single SQL migration file tracked by version."""

    version: str
    script_path: Path


def _open_migrated(database_path: Path) -> sqlite3.Connection:
    """Open a connection with Row factory set for column-name access."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    _ = connection.execute("PRAGMA foreign_keys = ON")
    return connection


def connect_migrated_sqlite_database(database_path: Path) -> sqlite3.Connection:
    """Upgrade the database schema, then return an open connection."""
    upgrade_sqlite_database(database_path)
    return _open_migrated(database_path)


def upgrade_sqlite_database(database_path: Path) -> None:
    """Apply pending migrations to bring the database schema up to date."""
    with _open_migrated(database_path) as connection:
        _ = connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at_utc TEXT NOT NULL"
            ")"
        )
        rows = fetchall_rows(connection, "SELECT version FROM schema_migrations")
        applied_versions = {
            read_required_text(row["version"], field_name="version") for row in rows
        }
        for migration in _load_migrations():
            if migration.version in applied_versions:
                continue
            script = migration.script_path.read_text(encoding="utf-8")
            _ = connection.executescript(script)
            _ = connection.execute(
                "INSERT INTO schema_migrations (version, applied_at_utc) VALUES (?, ?)",
                (migration.version, datetime.now(tz=UTC).isoformat()),
            )


def _load_migrations() -> tuple[SqliteMigration, ...]:
    versions_dir = Path(__file__).resolve().parents[3] / "alembic" / "versions"
    return tuple(
        SqliteMigration(version=script_path.stem, script_path=script_path)
        for script_path in sorted(versions_dir.glob("*.sql"))
    )
