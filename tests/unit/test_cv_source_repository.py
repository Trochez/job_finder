"""Unit tests for CvSourceSettingsRepository with in-memory SQLite."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

import pytest
from src.job_finder.adapters.repositories.cv_source import (
    CvSourceSettingsRepository,
)

if TYPE_CHECKING:
    from collections.abc import Generator

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS cv_source_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    renderer_type TEXT NOT NULL CHECK (renderer_type IN ('local', 'overleaf')),
    overleaf_project_id TEXT,
    active_version TEXT,
    candidate_profile_id TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE(candidate_profile_id)
);
"""


@pytest.fixture
def connection() -> Generator[sqlite3.Connection, None, None]:
    """Provide an in-memory SQLite database with the cv_source_settings table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(_CREATE_SQL)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def repo(connection: sqlite3.Connection) -> CvSourceSettingsRepository:
    """Provide a CvSourceSettingsRepository backed by the in-memory database."""
    return CvSourceSettingsRepository(connection)


class TestCvSourceSettingsRepository:
    """Tests for CvSourceSettingsRepository."""

    def test_upsert_settings_creates_row(
        self,
        repo: CvSourceSettingsRepository,
        connection: sqlite3.Connection,
    ) -> None:
        """Happy path: upsert_settings inserts a new row."""
        repo.upsert_settings(
            renderer_type="local",
            overleaf_project_id=None,
            active_version="v1.0.0",
            candidate_profile_id="default",
        )

        cursor = connection.execute(
            "SELECT renderer_type, active_version "
            "FROM cv_source_settings WHERE candidate_profile_id = ?",
            ("default",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["renderer_type"] == "local"
        assert row["active_version"] == "v1.0.0"

    def test_get_settings_returns_none_when_not_found(
        self,
        repo: CvSourceSettingsRepository,
    ) -> None:
        """get_settings returns None for a missing candidate_profile_id."""
        result = repo.get_settings(candidate_profile_id="nonexistent")
        assert result is None

    def test_upsert_settings_updates_existing(
        self,
        repo: CvSourceSettingsRepository,
        connection: sqlite3.Connection,
    ) -> None:
        """Upsert updates an existing row with same candidate_profile_id."""
        repo.upsert_settings(
            renderer_type="local",
            overleaf_project_id=None,
            active_version="v1.0.0",
            candidate_profile_id="default",
        )

        repo.upsert_settings(
            renderer_type="overleaf",
            overleaf_project_id="0123456789abcdef01234567",
            active_version="v2.0.0",
            candidate_profile_id="default",
        )

        cursor = connection.execute(
            "SELECT renderer_type, overleaf_project_id, active_version "
            "FROM cv_source_settings WHERE candidate_profile_id = ?",
            ("default",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["renderer_type"] == "overleaf"
        assert row["overleaf_project_id"] == "0123456789abcdef01234567"
        assert row["active_version"] == "v2.0.0"

    def test_get_settings_returns_correct_fields(
        self,
        repo: CvSourceSettingsRepository,
    ) -> None:
        """get_settings returns a CvSourceSettings with all fields populated."""
        repo.upsert_settings(
            renderer_type="overleaf",
            overleaf_project_id="abcdef0123456789abcdef01",
            active_version="v1.1.0",
            candidate_profile_id="profile-42",
        )

        result = repo.get_settings(candidate_profile_id="profile-42")
        assert result is not None
        assert result.renderer_type == "overleaf"
        assert result.overleaf_project_id == "abcdef0123456789abcdef01"
        assert result.active_version == "v1.1.0"
        assert result.candidate_profile_id == "profile-42"
        assert result.updated_at is not None

    def test_upsert_settings_on_conflict_updates(
        self,
        repo: CvSourceSettingsRepository,
        connection: sqlite3.Connection,
    ) -> None:
        """Multiple upserts update in place, no duplicate rows."""
        repo.upsert_settings(
            renderer_type="local",
            overleaf_project_id=None,
            active_version="v1.0.0",
            candidate_profile_id="dup-test",
        )
        repo.upsert_settings(
            renderer_type="overleaf",
            overleaf_project_id="abcdabcdabcdabcdabcdabcd",
            active_version="v2.0.0",
            candidate_profile_id="dup-test",
        )

        cursor = connection.execute(
            "SELECT COUNT(*) as cnt "
            "FROM cv_source_settings WHERE candidate_profile_id = ?",
            ("dup-test",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["cnt"] == 1

    def test_get_settings_returns_none_after_delete(
        self,
        repo: CvSourceSettingsRepository,
        connection: sqlite3.Connection,
    ) -> None:
        """After manual deletion, get_settings returns None."""
        repo.upsert_settings(
            renderer_type="local",
            overleaf_project_id=None,
            active_version="v1.0.0",
            candidate_profile_id="transient",
        )

        connection.execute(
            "DELETE FROM cv_source_settings WHERE candidate_profile_id = ?",
            ("transient",),
        )

        result = repo.get_settings(candidate_profile_id="transient")
        assert result is None
