from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3

    from tests.conftest import DeterministicClock, DeterministicUuidFactory
    from tests.fakes import FakeMcpClient, FakeRenderer, FakeTelegramClient


def test_deterministic_clock_and_uuid_fixtures(
    deterministic_clock: DeterministicClock,
    deterministic_uuid_factory: DeterministicUuidFactory,
) -> None:
    # Given: deterministic time and ID fixtures supplied by the harness.
    expected_now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    # When: tests ask for the current time and two UUIDs.
    now = deterministic_clock.now()
    first_uuid = deterministic_uuid_factory()
    second_uuid = deterministic_uuid_factory()

    # Then: every run observes the same stable values in sequence.
    assert now == expected_now
    assert str(first_uuid) == "00000000-0000-4000-8000-000000000001"
    assert str(second_uuid) == "00000000-0000-4000-8000-000000000002"


def test_sqlite_fixture_is_isolated(sqlite_connection: sqlite3.Connection) -> None:
    # Given: a temporary SQLite connection owned by this test.
    _ = sqlite_connection.execute("CREATE TABLE evidence (path TEXT NOT NULL)")

    # When: the test writes data to that database.
    _ = sqlite_connection.execute(
        "INSERT INTO evidence (path) VALUES (?)",
        (".omo/state/omo-team/job-finder-wave1/workers/worker-2/result.md",),
    )
    rows = sqlite_connection.execute("SELECT path FROM evidence").fetchall()

    # Then: the connection behaves like a real isolated SQLite database.
    assert rows == [
        (".omo/state/omo-team/job-finder-wave1/workers/worker-2/result.md",),
    ]


def test_fake_adapter_seams_record_without_network(
    fake_mcp: FakeMcpClient,
    fake_telegram: FakeTelegramClient,
    fake_renderer: FakeRenderer,
) -> None:
    # Given: fake-only seams for every external service lane M5 may exercise.
    fake_mcp.seed_tool_result("context7", "library-id:/pytest-dev/pytest")

    # When: callers use the seams through their public test APIs.
    mcp_result = fake_mcp.call_tool("context7", "pytest fixtures")
    fake_telegram.send_message(chat_id="team", text="harness ready")
    rendered = fake_renderer.render_markdown("# Harness")

    # Then: calls are deterministic and fully inspectable without real clients.
    assert mcp_result == "library-id:/pytest-dev/pytest"
    assert fake_mcp.calls == [("context7", "pytest fixtures")]
    assert fake_telegram.messages == [("team", "harness ready")]
    assert rendered == "<h1>Harness</h1>"
    assert fake_renderer.rendered_markdown == ["# Harness"]


def test_evidence_dir_uses_worker_lane_convention(evidence_dir: Path) -> None:
    # Given: the harness evidence directory fixture.
    expected_suffix = Path(
        ".omo/state/omo-team/job-finder-wave1/workers/worker-2/evidence",
    )

    # When: a test asks where worker-2 evidence should be written.
    relative = evidence_dir.relative_to(Path.cwd())

    # Then: the path follows the approved team/worker convention.
    assert relative == expected_suffix
