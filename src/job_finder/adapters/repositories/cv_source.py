"""CV source settings repository backed by SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ._query_helpers import (
    execute_sql,
    fetchone_row,
    read_optional_text,
    read_required_text,
)

if TYPE_CHECKING:
    import sqlite3


@dataclass(frozen=True, slots=True)
class CvSourceSettings:
    """Immutable CV source settings record."""

    renderer_type: str
    overleaf_project_id: str | None
    active_version: str | None
    candidate_profile_id: str | None
    updated_at: str


class CvSourceSettingsRepository:
    """Repository for persisting CV source settings to SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Store the SQLite connection for future queries."""
        self._connection = connection

    def upsert_settings(
        self,
        *,
        renderer_type: str,
        overleaf_project_id: str | None,
        active_version: str | None,
        candidate_profile_id: str | None,
    ) -> None:
        """Insert or update CV source settings for a candidate profile."""
        now = datetime.now(UTC).isoformat()
        execute_sql(
            self._connection,
            "INSERT INTO cv_source_settings "
            "(renderer_type, overleaf_project_id, active_version, "
            "candidate_profile_id, updated_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(candidate_profile_id) DO UPDATE SET "
            "renderer_type=excluded.renderer_type, "
            "overleaf_project_id=excluded.overleaf_project_id, "
            "active_version=excluded.active_version, "
            "updated_at=excluded.updated_at",
            (
                renderer_type,
                overleaf_project_id,
                active_version,
                candidate_profile_id,
                now,
            ),
        )

    def get_settings(
        self,
        *,
        candidate_profile_id: str,
    ) -> CvSourceSettings | None:
        """Fetch CV source settings for a candidate profile, or None."""
        row = fetchone_row(
            self._connection,
            "SELECT * FROM cv_source_settings "
            "WHERE candidate_profile_id = ?",
            (candidate_profile_id,),
        )
        if row is None:
            return None
        return CvSourceSettings(
            renderer_type=read_required_text(
                row["renderer_type"], field_name="renderer_type",
            ),
            overleaf_project_id=read_optional_text(
                row["overleaf_project_id"],
                field_name="overleaf_project_id",
            ),
            active_version=read_optional_text(
                row["active_version"], field_name="active_version",
            ),
            candidate_profile_id=read_optional_text(
                row["candidate_profile_id"],
                field_name="candidate_profile_id",
            ),
            updated_at=read_required_text(
                row["updated_at"], field_name="updated_at",
            ),
        )
