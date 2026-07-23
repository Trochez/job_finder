from __future__ import annotations

import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from src.job_finder.adapters.db import bootstrap_private_sqlite_storage
from src.job_finder.adapters.migrations import (
    connect_migrated_sqlite_database,
)
from src.job_finder.adapters.settings import PrivateSettings

from .fakes import FakeMcpClient, FakeRenderer, FakeTelegramClient
from .fakes.sentinels import SentinelDataSet

if TYPE_CHECKING:
    from collections.abc import Generator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@dataclass(frozen=True, slots=True)
class DeterministicClock:
    current_time: datetime = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current_time


class DeterministicUuidFactory:
    def __init__(self) -> None:
        self._next_id: int = 1

    def __call__(self) -> uuid.UUID:
        value = uuid.UUID(f"00000000-0000-4000-8000-{self._next_id:012d}")
        self._next_id += 1
        return value


@pytest.fixture
def deterministic_clock() -> DeterministicClock:
    return DeterministicClock()


@pytest.fixture
def deterministic_uuid_factory() -> DeterministicUuidFactory:
    return DeterministicUuidFactory()


@pytest.fixture
def sqlite_connection(tmp_path: Path) -> Generator[sqlite3.Connection, None, None]:
    database_path = tmp_path / "job_finder_test.sqlite3"
    with sqlite3.connect(database_path) as connection:
        yield connection


@pytest.fixture
def fake_mcp() -> FakeMcpClient:
    return FakeMcpClient()


@pytest.fixture
def fake_telegram() -> FakeTelegramClient:
    return FakeTelegramClient()


@pytest.fixture
def fake_renderer() -> FakeRenderer:
    return FakeRenderer()


@pytest.fixture
def evidence_dir() -> Path:
    path = Path.cwd() / ".omo/state/omo-team/job-finder-wave1/workers/worker-2/evidence"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── Shared fixtures for e2e and security tests ──────────────────────────────


@pytest.fixture
def sentinel_data_set() -> SentinelDataSet:
    """Provide a fresh set of sentinel data for security/privacy tests."""
    return SentinelDataSet()


@pytest.fixture
def e2e_sqlite_connection(
    tmp_path: Path,
) -> Generator[sqlite3.Connection, None, None]:
    """Bootstrapped + migrated SQLite database for end-to-end tests."""
    settings = PrivateSettings.from_paths(
        app_data_dir=tmp_path / "private",
        sqlite_database_name="e2e_test.sqlite3",
    )
    _ = bootstrap_private_sqlite_storage(settings)
    connection = connect_migrated_sqlite_database(settings.sqlite_database_path)
    try:
        yield connection
    finally:
        connection.close()
