"""Tests for the CV source route controller."""

from __future__ import annotations

import sqlite3
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


@pytest.fixture
def base_deps(tmp_path: Path) -> Generator[AppDependencies, None, None]:
    """Minimal test dependencies with a temporary database."""
    settings = PrivateSettings.from_paths(
        app_data_dir=tmp_path,
        sqlite_database_name="cv_source_test.sqlite3",
    )
    database_path = settings.sqlite_database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(mode=0o600)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA user_version = 1")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    # Schema: candidate_profiles + cv_source_settings with FK to
    # candidate_profiles(profile_id). Without these tables the POST route's
    # inner except (OperationalError) masks the FK bug we test here.
    connection.execute(
        "CREATE TABLE IF NOT EXISTS candidate_profiles ("
        "profile_id TEXT PRIMARY KEY,"
        "candidate_id TEXT NOT NULL UNIQUE,"
        "active_version_id TEXT NOT NULL,"
        "timezone_name TEXT NOT NULL,"
        "created_at_utc TEXT NOT NULL"
        ")",
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS cv_source_settings ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "renderer_type TEXT NOT NULL CHECK (renderer_type IN ('local', 'overleaf')),"
        "overleaf_project_id TEXT,"
        "active_version TEXT,"
        "candidate_profile_id TEXT,"
        "updated_at TEXT NOT NULL,"
        "FOREIGN KEY (candidate_profile_id) "
        "REFERENCES candidate_profiles(profile_id) ON DELETE RESTRICT,"
        "UNIQUE(candidate_profile_id)"
        ")",
    )
    connection.commit()

    deps = AppDependencies(
        settings=settings,
        connection=connection,
        workflow_repo=SqliteWorkflowRepository(connection),
        notifier=FakeTelegramNotifier(),
        mcp_available=False,
    )
    yield deps
    deps.shutdown()


class TestCvSourceRoutes:
    """Test suite for /cv-source routes."""

    def test_get_returns_200(self, base_deps: AppDependencies) -> None:
        """GET /cv-source returns 200."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/cv-source")
        assert response.status_code == 200

    def test_get_contains_form(self, base_deps: AppDependencies) -> None:
        """GET /cv-source renders a form with profile version and renderer fields."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/cv-source")
        html = response.text
        assert 'name="profile_version"' in html
        assert 'name="renderer_path"' in html

    def test_get_contains_profile_versions(self, base_deps: AppDependencies) -> None:
        """Rendered page includes profile version options."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/cv-source")
        assert "v1.0.0" in response.text
        assert "v2.0.0" in response.text

    def test_post_saves_and_redirects(self, base_deps: AppDependencies) -> None:
        """POST /cv-source saves data and redirects."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.1.0",
                    "renderer_path": "/usr/local/bin/cv_renderer",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "/cv-source" in response.headers.get("location", "")

    def test_post_redirect_followed_shows_success(
        self, base_deps: AppDependencies,
    ) -> None:
        """POST followed by GET shows success flash."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v2.0.0",
                    "renderer_path": "/opt/renderer/cv",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "CV source settings saved" in response.text

    def test_post_empty_renderer_path(self, base_deps: AppDependencies) -> None:
        """POST with empty renderer path still succeeds."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/cv-source",
                data={
                    "profile_version": "v1.0.0",
                    "renderer_path": "",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "CV source settings saved" in response.text

    def test_get_form_has_submit_button(self, base_deps: AppDependencies) -> None:
        """Form has a save button."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/cv-source")
        assert 'type="submit"' in response.text
        assert "Save" in response.text
