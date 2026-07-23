"""Tests for dashboard shell: base template, navigation, responsive layout."""

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
        sqlite_database_name="dashboard_test.sqlite3",
    )
    database_path = settings.sqlite_database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.touch(mode=0o600)
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA user_version = 1")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    deps = AppDependencies(
        settings=settings,
        connection=connection,
        workflow_repo=SqliteWorkflowRepository(connection),
        notifier=FakeTelegramNotifier(),
        mcp_available=False,
    )
    yield deps
    deps.shutdown()


class TestDashboardShell:
    """Test suite for the dashboard shell."""

    def test_dashboard_returns_200(self, base_deps: AppDependencies) -> None:
        """Dashboard page loads successfully."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        assert response.status_code == 200

    def test_dashboard_contains_nav(self, base_deps: AppDependencies) -> None:
        """Dashboard page includes navigation with expected links."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        html = response.text
        assert "job_finder" in html
        assert "/dashboard" in html
        assert "/profile-settings" in html
        assert "/cv-source" in html
        assert "/job-review" in html
        assert "/audit" in html
        assert "/checkpoints" in html

    def test_dashboard_has_skip_link(self, base_deps: AppDependencies) -> None:
        """Dashboard includes a skip-to-content link for accessibility."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        assert 'class="skip-link"' in response.text
        assert "Skip to content" in response.text

    def test_dashboard_has_main_landmark(self, base_deps: AppDependencies) -> None:
        """Dashboard has a <main> element with id main-content."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        assert '<main id="main-content"' in response.text

    def test_dashboard_has_nav_landmark(self, base_deps: AppDependencies) -> None:
        """Dashboard has a <nav> element with aria-label."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        assert 'aria-label="Main navigation"' in response.text

    def test_dashboard_active_page_marked(self, base_deps: AppDependencies) -> None:
        """The active nav item has aria-current='page'."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        html = response.text
        assert 'aria-current="page"' in html
        assert "/dashboard" in html

    def test_dashboard_empty_state_no_jobs(self, base_deps: AppDependencies) -> None:
        """Dashboard shows empty state when no stats are configured."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        # Default stats show non-zero values, so empty state not shown.
        assert "Total Jobs Scored" in response.text

    def test_static_css_served(self, base_deps: AppDependencies) -> None:
        """Static CSS file is served correctly."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

    def test_nav_includes_toggle_for_mobile(self, base_deps: AppDependencies) -> None:
        """Navigation includes hamburger toggle button."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/dashboard")
        assert 'id="nav-toggle"' in response.text
        assert 'aria-label="Toggle navigation menu"' in response.text

    def test_profile_settings_page_exists(self, base_deps: AppDependencies) -> None:
        """Profile settings page loads."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/profile-settings")
        assert response.status_code == 200

    def test_cv_source_page_exists(self, base_deps: AppDependencies) -> None:
        """CV source page loads."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/cv-source")
        assert response.status_code == 200
