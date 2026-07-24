"""Integration tests for Overleaf CV source form submission and validation."""

from __future__ import annotations

import sqlite3
import stat
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from src.job_finder.adapters.notifications.telegram import FakeTelegramNotifier
from src.job_finder.adapters.repositories.workflow import SqliteWorkflowRepository
from src.job_finder.adapters.settings import PrivateSettings
from src.job_finder.web.app import create_app, inject_test_deps
from src.job_finder.web.deps import AppDependencies

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

_CREATE_CV_SOURCE_TABLE = """
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

_VALID_PROJECT_ID = "0123456789abcdef01234567"


@pytest.fixture
def deps_with_secrets(
    tmp_path: Path,
) -> Generator[AppDependencies, None, None]:
    """Test dependencies with a secrets reference path and cv_source_settings table."""
    secrets_path = tmp_path / "secrets"
    secrets_path.mkdir(parents=True, exist_ok=True)

    settings = PrivateSettings.from_paths(
        app_data_dir=tmp_path,
        sqlite_database_name="cv_source_overleaf_test.sqlite3",
        secrets_reference_path=secrets_path,
    )
    database_path = settings.sqlite_database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(mode=0o600)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.execute("PRAGMA user_version = 1")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(_CREATE_CV_SOURCE_TABLE)

    deps = AppDependencies(
        settings=settings,
        connection=connection,
        workflow_repo=SqliteWorkflowRepository(connection),
        notifier=FakeTelegramNotifier(),
        mcp_available=False,
    )
    yield deps
    deps.shutdown()


@pytest.fixture
def deps_basic(tmp_path: Path) -> Generator[AppDependencies, None, None]:
    """Test dependencies without secrets reference path."""
    settings = PrivateSettings.from_paths(
        app_data_dir=tmp_path,
        sqlite_database_name="cv_source_basic_test.sqlite3",
    )
    database_path = settings.sqlite_database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(mode=0o600)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.execute("PRAGMA user_version = 1")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(_CREATE_CV_SOURCE_TABLE)

    deps = AppDependencies(
        settings=settings,
        connection=connection,
        workflow_repo=SqliteWorkflowRepository(connection),
        notifier=FakeTelegramNotifier(),
        mcp_available=False,
    )
    yield deps
    deps.shutdown()


class TestCvSourceOverleafRoutes:
    """Integration tests for Overleaf CV source routes."""

    def test_get_cv_source_form(self, deps_basic: AppDependencies) -> None:
        """GET /cv-source returns 200 and contains renderer_type field."""
        inject_test_deps(deps_basic)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/cv-source")
        assert response.status_code == 200
        assert 'name="renderer_type"' in response.text
        assert "Overleaf Integration" in response.text

    def test_post_cv_source_local(
        self,
        deps_with_secrets: AppDependencies,
    ) -> None:
        """POST with local renderer_type saves and redirects."""
        inject_test_deps(deps_with_secrets)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.0.0",
                    "renderer_path": "/usr/local/bin/renderer",
                    "renderer_type": "local",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "/cv-source" in response.headers.get("location", "")

    def test_post_cv_source_overleaf(
        self,
        deps_with_secrets: AppDependencies,
    ) -> None:
        """POST with valid overleaf renderer_type saves and redirects."""
        inject_test_deps(deps_with_secrets)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v2.0.0",
                    "renderer_type": "overleaf",
                    "overleaf_project_id": _VALID_PROJECT_ID,
                    "overleaf_token": "ghp_abc123def456",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "CV source settings saved" in response.text

    def test_post_cv_source_invalid_project_id(
        self,
        deps_basic: AppDependencies,
    ) -> None:
        """POST with bad project_id format shows error."""
        inject_test_deps(deps_basic)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.0.0",
                    "renderer_type": "overleaf",
                    "overleaf_project_id": "not-a-valid-hex",
                    "overleaf_token": "some-token",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Invalid Overleaf project ID" in response.text
        assert "24 hex chars" in response.text

    def test_post_cv_source_missing_token(
        self,
        deps_basic: AppDependencies,
    ) -> None:
        """POST overleaf without token shows error."""
        inject_test_deps(deps_basic)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.0.0",
                    "renderer_type": "overleaf",
                    "overleaf_project_id": _VALID_PROJECT_ID,
                    "overleaf_token": "",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Overleaf token required" in response.text

    def test_post_cv_source_token_written_to_file(
        self,
        deps_with_secrets: AppDependencies,
    ) -> None:
        """Verify token file is written with 0o600 permissions."""
        inject_test_deps(deps_with_secrets)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.0.0",
                    "renderer_type": "overleaf",
                    "overleaf_project_id": _VALID_PROJECT_ID,
                    "overleaf_token": "super-secret-token-value",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200

        secrets = deps_with_secrets.settings.secrets_reference_path
        assert secrets is not None
        token_path = secrets / "overleaf_token"
        assert token_path.exists()
        assert token_path.read_text(encoding="utf-8") == "super-secret-token-value"

        actual_mode = stat.S_IMODE(token_path.stat().st_mode)
        assert actual_mode == 0o600

    def test_post_cv_source_settings_persisted(
        self,
        deps_with_secrets: AppDependencies,
    ) -> None:
        """Verify DB row is created after POST with overleaf data."""
        inject_test_deps(deps_with_secrets)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v2.0.0",
                    "renderer_type": "overleaf",
                    "overleaf_project_id": _VALID_PROJECT_ID,
                    "overleaf_token": "persist-test-token",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200

        cursor = deps_with_secrets.connection.execute(
            "SELECT renderer_type, overleaf_project_id, active_version "
            "FROM cv_source_settings WHERE candidate_profile_id = ?",
            ("default",),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["renderer_type"] == "overleaf"
        assert row["overleaf_project_id"] == _VALID_PROJECT_ID
        assert row["active_version"] == "v2.0.0"

    def test_post_local_without_overleaf_fields(
        self,
        deps_basic: AppDependencies,
    ) -> None:
        """POST with local renderer_type succeeds even without overleaf fields."""
        inject_test_deps(deps_basic)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.1.0",
                    "renderer_path": "/custom/path",
                    "renderer_type": "local",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "CV source settings saved" in response.text
