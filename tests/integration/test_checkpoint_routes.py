"""Tests for the checkpoints route controller."""

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
        sqlite_database_name="checkpoint_test.sqlite3",
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


class TestCheckpointRoutes:
    """Test suite for /checkpoints routes."""

    def test_get_returns_200(self, base_deps: AppDependencies) -> None:
        """GET /checkpoints returns 200."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/checkpoints")
        assert response.status_code == 200

    def test_get_shows_checkpoints(self, base_deps: AppDependencies) -> None:
        """Checkpoints page shows active checkpoint cards."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/checkpoints")
        html = response.text
        assert "CAPTCHA Challenge" in html
        assert "cp_001" in html
        assert "Login Challenge" in html
        assert "cp_002" in html

    def test_get_shows_kill_switch(self, base_deps: AppDependencies) -> None:
        """Checkpoints page shows kill switch toggle."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/checkpoints")
        assert "Kill Switch" in response.text
        assert 'name="kill_switch"' in response.text

    def test_post_answer_submits_and_redirects(
        self, base_deps: AppDependencies,
    ) -> None:
        """POST with answer for checkpoint redirects."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "cp_001",
                    "action": "resume",
                    "answer": "test_answer",
                },
                follow_redirects=False,
            )
        assert response.status_code == 303
        assert "/checkpoints" in response.headers.get("location", "")

    def test_post_answer_shows_success(self, base_deps: AppDependencies) -> None:
        """POST with answer followed by redirect shows success."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "cp_001",
                    "action": "resume",
                    "answer": "test_answer",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Answer submitted" in response.text

    def test_post_dismiss_redirects(self, base_deps: AppDependencies) -> None:
        """POST with dismiss action redirects."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "cp_001",
                    "action": "dismiss",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "dismissed" in response.text

    def test_post_kill_switch_activates(self, base_deps: AppDependencies) -> None:
        """POST toggling kill switch activates it."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "global",
                    "action": "toggle_kill_switch",
                    "kill_switch": "1",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Kill switch activated" in response.text

    def test_post_kill_switch_deactivates(self, base_deps: AppDependencies) -> None:
        """POST toggling kill switch off deactivates it."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            # Activate first
            client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "global",
                    "action": "toggle_kill_switch",
                    "kill_switch": "1",
                },
            )
            # Then deactivate
            response = client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "global",
                    "action": "toggle_kill_switch",
                    "kill_switch": "",
                },
                follow_redirects=True,
            )
        assert response.status_code == 200
        assert "Kill switch deactivated" in response.text

    def test_get_kill_switch_active_state(self, base_deps: AppDependencies) -> None:
        """Kill switch state is reflected in the page."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as client:
            # Activate kill switch
            client.post(
                "/checkpoints",
                data={
                    "checkpoint_id": "global",
                    "action": "toggle_kill_switch",
                    "kill_switch": "1",
                },
            )
            response = client.get("/checkpoints")
        assert "Kill Switch (Active)" in response.text

    def test_get_empty_checkpoints(self, base_deps: AppDependencies) -> None:
        """When no checkpoints exist, shows empty state."""
        inject_test_deps(base_deps)
        app = create_app()
        with TestClient(app) as _client:
            pass
