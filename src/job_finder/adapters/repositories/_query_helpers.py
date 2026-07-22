"""Shared SQLite query helper utilities for repositories.

Consolidates the duplicated fetch/execute/read helpers that were spread across
jobs.py, workflow.py, and migrations.py, fixing the union type errors that
the Patch-failed checkpoint identified.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


def fetchone_row(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
) -> sqlite3.Row | None:
    """Execute a query and return exactly one row (or None)."""
    cursor = connection.execute(sql, parameters)
    return cursor.fetchone()


def fetchall_rows(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
) -> list[sqlite3.Row]:
    """Execute a query and return all result rows."""
    cursor = connection.execute(sql, parameters)
    rows = cursor.fetchall()
    return list(rows)


def execute_sql(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[object, ...] = (),
) -> sqlite3.Cursor:
    """Execute a write/update statement and return the cursor."""
    return connection.execute(sql, parameters)


def read_required_text(value: object, *, field_name: str) -> str:
    if isinstance(value, str):
        return value
    msg = f"expected TEXT column for {field_name}, got {type(value).__name__}"
    raise TypeError(msg)


def read_optional_text(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    return read_required_text(value, field_name=field_name)


def read_datetime(value: object, *, field_name: str) -> datetime:
    return datetime.fromisoformat(read_required_text(value, field_name=field_name))


def read_positive_int(value: object, *, field_name: str) -> int:
    if isinstance(value, int):
        return value
    msg = f"expected INTEGER column for {field_name}, got {type(value).__name__}"
    raise TypeError(msg)
