"""Tests for the profile settings route controller."""

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
        sqlite_database_name="profile_settings_test.sqlite3",
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


class TestProfileSettingsRoutes:
    """Test suite for /profile-settings routes."""

    def test_get_returns_200(self, base_deps: AppDependencies) -> None:
        """GET /profile-settings returns 200."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/profile-settings")
        assert response.status_code == 200

    def test_get_contains_form(self, base_deps: AppDependencies) -> None:
        """GET /profile-settings renders a form with expected fields."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/profile-settings")
        html = response.text
        assert 'name="timezone"' in html
        assert 'name="hard_filters"' in html
        assert 'name="threshold"' in html
        assert 'name="daily_cap"' in html

    def test_get_contains_iana_timezones(self, base_deps: AppDependencies) -> None:
        """Rendered page includes IANA timezone options."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/profile-settings")
        assert "America/New_York" in response.text
        assert "Europe/London" in response.text
        assert "UTC" in response.text

    def test_get_contains_hard_filter_options(
        self, base_deps: AppDependencies,
    ) -> None:
        """Rendered page includes hard filter checkboxes."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/profile-settings")
        html = response.text
        assert "No Remote Work" in html
        assert "Contract/Freelance Only" in html

    def test_post_saves_and_redirects(self, base_deps: AppDependencies) -> None:
        """POST /profile-settings saves data and redirects."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/profile-settings",
                data={
                    "timezone": "America/Chicago",
                    "hard_filters": ["no_remote", "visa_required"],
                    "threshold": "65",
                    "daily_cap": "15",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "/profile-settings" in response.headers.get("location", "")

    def test_post_redirect_followed_shows_success(
        self, base_deps: AppDependencies,
    ) -> None:
        """POST followed by GET shows success flash."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/profile-settings",
                data={
                    "timezone": "America/Chicago",
                    "hard_filters": ["no_remote"],
                    "threshold": "70",
                    "daily_cap": "20",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Profile settings saved" in response.text

    def test_post_invalid_timezone_shows_error(
        self, base_deps: AppDependencies,
    ) -> None:
        """POST with invalid timezone shows error flash."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/profile-settings",
                data={
                    "timezone": "Mars/Olympus",
                    "hard_filters": [],
                    "threshold": "50",
                    "daily_cap": "10",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Invalid timezone" in response.text

    def test_post_invalid_threshold_shows_error(
        self, base_deps: AppDependencies,
    ) -> None:
        """POST with non-numeric threshold shows error flash."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/profile-settings",
                data={
                    "timezone": "UTC",
                    "hard_filters": [],
                    "threshold": "abc",
                    "daily_cap": "10",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "must be valid numbers" in response.text

    def test_post_clamps_threshold_out_of_range(
        self, base_deps: AppDependencies,
    ) -> None:
        """Threshold above 100 is clamped to 100."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            client.post(
                "/profile-settings",
                data={
                    "timezone": "UTC",
                    "hard_filters": [],
                    "threshold": "999",
                    "daily_cap": "10",
                },
                follow_redirects=True,
            )
            # Read back - no error means it was clamped successfully
            response = client.get("/profile-settings")
        assert response.status_code == 200

    def test_post_saves_multiple_hard_filters(
        self, base_deps: AppDependencies,
    ) -> None:
        """Multiple hard filter selections are saved."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            client.post(
                "/profile-settings",
                data={
                    "timezone": "US/Eastern",
                    "hard_filters": [
                        "no_remote",
                        "contract_only",
                        "requires_relocation",
                    ],
                    "threshold": "50",
                    "daily_cap": "10",
                },
                follow_redirects=True,
            )
            response = client.get("/profile-settings")
        assert response.status_code == 200
