"""Tests for the FastAPI application lifespan (startup/shutdown)."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.job_finder.adapters.notifications.telegram import FakeTelegramNotifier
from src.job_finder.adapters.repositories.workflow import (
    SqliteWorkflowRepository,
)
from src.job_finder.adapters.settings import PrivateSettings
from src.job_finder.web.app import create_app, inject_test_deps
from src.job_finder.web.deps import AppDependencies

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def test_deps(tmp_path: Path) -> Generator[AppDependencies, None, None]:
    """Build test dependencies backed by a temporary SQLite database."""
    settings = PrivateSettings.from_paths(
        app_data_dir=tmp_path,
        sqlite_database_name="test.sqlite3",
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


def test_app_starts_with_test_deps(test_deps: AppDependencies) -> None:
    """Verify the application starts and shuts down cleanly."""
    inject_test_deps(test_deps)
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200, "health endpoint should respond"
    assert response.json()["status"] == "ok"


def test_lifespan_shuts_down_cleanly(test_deps: AppDependencies) -> None:
    """Verify that shutdown runs without error."""
    inject_test_deps(test_deps)
    app = create_app()
    with TestClient(app):
        pass  # startup + shutdown
    # If we reach here without exception, shutdown was clean.
