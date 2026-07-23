"""Tests for job review and audit route controllers."""

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
        sqlite_database_name="job_audit_test.sqlite3",
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


class TestJobReviewRoutes:
    """Test suite for /job-review routes."""

    def test_job_review_returns_200(self, base_deps: AppDependencies) -> None:
        """GET /job-review returns 200."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/job-review")
        assert response.status_code == 200

    def test_job_review_contains_table(self, base_deps: AppDependencies) -> None:
        """Job review page contains a table with expected columns."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/job-review")
        html = response.text
        assert "<table>" in html
        assert "Company" in html
        assert "Title" in html
        assert "Score" in html
        assert "Eligibility" in html
        assert "Route" in html

    def test_job_review_shows_sample_jobs(self, base_deps: AppDependencies) -> None:
        """Job review shows sample job entries."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/job-review")
        html = response.text
        assert "Acme Corp" in html
        assert "Senior Software Engineer" in html

    def test_job_review_shows_eligibility_badges(
        self, base_deps: AppDependencies,
    ) -> None:
        """Job review shows eligibility badges."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/job-review")
        assert "Eligible" in response.text
        assert "Ineligible" in response.text

    def test_job_review_has_no_empty_state_with_data(
        self, base_deps: AppDependencies,
    ) -> None:
        """Job review shows data, not empty state."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/job-review")
        assert "No jobs scored yet" not in response.text


class TestAuditRoutes:
    """Test suite for /audit routes."""

    def test_audit_returns_200(self, base_deps: AppDependencies) -> None:
        """GET /audit returns 200."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit")
        assert response.status_code == 200

    def test_audit_contains_search_form(self, base_deps: AppDependencies) -> None:
        """Audit page contains search and filter controls."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit")
        html = response.text
        assert 'name="search"' in html
        assert 'name="status"' in html
        assert 'type="submit"' in html

    def test_audit_shows_sample_records(self, base_deps: AppDependencies) -> None:
        """Audit page shows sample records."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit")
        html = response.text
        assert "job_001" in html
        assert "job_002" in html

    def test_audit_search_filters_results(self, base_deps: AppDependencies) -> None:
        """Search parameter filters audit results."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit?search=job_002")
        assert "job_002" in response.text
        assert "job_001" not in response.text

    def test_audit_status_filter(self, base_deps: AppDependencies) -> None:
        """Status filter narrows audit results."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit?status=error")
        assert "Scoring failed" in response.text

    def test_audit_empty_state_on_no_match(self, base_deps: AppDependencies) -> None:
        """Audit shows empty state when no records match."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit?search=zzzzz_nonexistent")
        assert "No audit records found" in response.text
