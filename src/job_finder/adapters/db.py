"""SQLite storage bootstrapping and private file-system setup."""

from __future__ import annotations

import os
import sqlite3
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .settings import (
    PRIVATE_DIRECTORY_MODE,
    PRIVATE_FILE_MODE,
    PrivateSettings,
    UnsafeConfiguration,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class BootstrappedSqliteStorage:
    """Result of bootstrapping a private SQLite storage location."""

    app_data_dir: Path
    database_path: Path


def bootstrap_private_sqlite_storage(
    settings: PrivateSettings,
) -> BootstrappedSqliteStorage:
    """Ensure app_data_dir exists with private mode, then create the database file."""
    settings.app_data_dir.mkdir(
        mode=PRIVATE_DIRECTORY_MODE, parents=True, exist_ok=True,
    )
    settings.app_data_dir.chmod(PRIVATE_DIRECTORY_MODE)
    _require_mode(
        settings.app_data_dir,
        expected_mode=PRIVATE_DIRECTORY_MODE,
        field_name="app_data_dir",
    )

    if (
        settings.sqlite_database_path.exists()
        and not settings.sqlite_database_path.is_file()
    ):
        msg = "sqlite_database_path"
        raise UnsafeConfiguration(
            msg,
            "must point to a SQLite file path",
        )

    file_descriptor = os.open(
        settings.sqlite_database_path,
        os.O_CREAT | os.O_RDWR,
        PRIVATE_FILE_MODE,
    )
    os.close(file_descriptor)
    settings.sqlite_database_path.chmod(PRIVATE_FILE_MODE)
    _require_mode(
        settings.sqlite_database_path,
        expected_mode=PRIVATE_FILE_MODE,
        field_name="sqlite_database_path",
    )

    connection = sqlite3.connect(settings.sqlite_database_path)
    try:
        _ = connection.execute("PRAGMA user_version = 1")
    finally:
        connection.close()

    return BootstrappedSqliteStorage(
        app_data_dir=settings.app_data_dir,
        database_path=settings.sqlite_database_path,
    )


def _require_mode(path: Path, *, expected_mode: int, field_name: str) -> None:
    actual_mode = stat.S_IMODE(path.stat().st_mode)
    if actual_mode != expected_mode:
        raise UnsafeConfiguration(
            field_name,
            f"must remain private with mode {oct(expected_mode)}",
        )
