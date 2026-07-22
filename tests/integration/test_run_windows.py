"""Integration tests for run-cycle orchestration and watermark management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from job_finder.adapters.cv_renderer.port import RenderedArtifactId, RenderResult

if TYPE_CHECKING:
    from pathlib import Path

    from job_finder.adapters.cv_renderer.port import RenderRequest

import pytest

from job_finder.adapters.db import bootstrap_private_sqlite_storage
from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.adapters.repositories.audit import SqliteAuditRepository
from job_finder.adapters.repositories.jobs import SqliteJobsRepository
from job_finder.adapters.repositories.workflow import (
    CandidateProfileRecord,
    RunWatermarkRecord,
    SqliteWorkflowRepository,
)
from job_finder.adapters.settings import PrivateSettings
from job_finder.application.run_cycle import (
    ConcurrentRunError,
    execute_run,
)
from job_finder.domain.ids import (
    CandidateId,
    CandidateProfileId,
    CandidateProfileVersionId,
    RunId,
)


class _StubMcpSource:
    """Minimal MCP source stub that returns no jobs."""

    def search_jobs(self, search: object) -> tuple[()]:  # type: ignore[override]
        return ()


class _StubRenderer:
    """Minimal renderer stub."""

    def render(self, request: RenderRequest) -> RenderResult:
        return RenderResult(
            artifact_id=RenderedArtifactId("stub"),
            output_path=request.output_path / "stub.tex",
            rendered_at=datetime.now(tz=UTC),
            fact_ids_used=(),
        )


class _StubNotifier:
    """Minimal notifier stub."""

    def send_message(self, chat_id: str, text: str) -> None:
        return None


class _FixedClock:
    """Minimal clock that returns a fixed time."""

    _now: datetime

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _bootstrap_all(
    tmp_path: Path,
) -> tuple[
    SqliteWorkflowRepository,
    SqliteJobsRepository,
    SqliteAuditRepository,
]:
    settings = PrivateSettings.from_paths(app_data_dir=tmp_path / "private")
    storage = bootstrap_private_sqlite_storage(settings)
    connection = connect_migrated_sqlite_database(storage.database_path)
    return (
        SqliteWorkflowRepository(connection),
        SqliteJobsRepository(connection),
        SqliteAuditRepository(connection),
    )


class TestRunWatermark:
    """Watermark creation and update behaviour."""

    def test_first_run_creates_watermark(
        self, tmp_path: Path,
    ) -> None:
        # Given
        workflow, _jobs, _audit = _bootstrap_all(tmp_path)
        profile_id = CandidateProfileId("profile-1")
        _ = workflow.upsert_candidate_profile(
            CandidateProfileRecord(
                profile_id=profile_id,
                candidate_id=CandidateId("candidate-1"),
                active_version=CandidateProfileVersionId("v1"),
                timezone_name="UTC",
                created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ),
        )

        # When
        workflow.save_run_watermark(
            RunWatermarkRecord(
                candidate_profile_id=profile_id,
                run_id=RunId("run-1"),
                previous_successful_watermark=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                successful_through=datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
            ),
        )

        # Then
        stored = workflow.get_run_watermark(profile_id)
        assert stored is not None
        assert stored.run_id == RunId("run-1")

    def test_second_run_updates_watermark(
        self, tmp_path: Path,
    ) -> None:
        # Given
        workflow, _jobs, _audit = _bootstrap_all(tmp_path)
        profile_id = CandidateProfileId("profile-2")
        _ = workflow.upsert_candidate_profile(
            CandidateProfileRecord(
                profile_id=profile_id,
                candidate_id=CandidateId("candidate-2"),
                active_version=CandidateProfileVersionId("v1"),
                timezone_name="UTC",
                created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ),
        )

        workflow.save_run_watermark(
            RunWatermarkRecord(
                candidate_profile_id=profile_id,
                run_id=RunId("run-1"),
                previous_successful_watermark=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                successful_through=datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
            ),
        )

        # When
        workflow.save_run_watermark(
            RunWatermarkRecord(
                candidate_profile_id=profile_id,
                run_id=RunId("run-2"),
                previous_successful_watermark=datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                successful_through=datetime(2026, 1, 3, 0, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 1, 3, 0, 0, 0, tzinfo=UTC),
            ),
        )

        # Then
        stored = workflow.get_run_watermark(profile_id)
        assert stored is not None
        assert stored.run_id == RunId("run-2")
        assert stored.previous_successful_watermark == datetime(
            2026, 1, 2, 0, 0, 0, tzinfo=UTC,
        )
        assert stored.successful_through == datetime(2026, 1, 3, 0, 0, 0, tzinfo=UTC)

    def test_watermark_not_found_returns_none(
        self, tmp_path: Path,
    ) -> None:
        # Given
        workflow, _jobs, _audit = _bootstrap_all(tmp_path)

        # When
        stored = workflow.get_run_watermark(CandidateProfileId("missing"))

        # Then
        assert stored is None


class TestConcurrentRunGuard:
    """Concurrent run detection from watermark timestamps."""

    def test_watermark_in_future_blocks_new_run(
        self, tmp_path: Path,
    ) -> None:
        """A watermark with successful_through in the future must raise."""
        clock_now = datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC)
        future_watermark = datetime(2026, 1, 3, 0, 0, 0, tzinfo=UTC)  # > now

        workflow, jobs, audit = _bootstrap_all(tmp_path)
        profile_id = CandidateProfileId("profile-concurrent")
        _ = workflow.upsert_candidate_profile(
            CandidateProfileRecord(
                profile_id=profile_id,
                candidate_id=CandidateId("candidate-concurrent"),
                active_version=CandidateProfileVersionId("v1"),
                timezone_name="UTC",
                created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ),
        )
        workflow.save_run_watermark(
            RunWatermarkRecord(
                candidate_profile_id=profile_id,
                run_id=RunId("run-future"),
                previous_successful_watermark=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                successful_through=future_watermark,
                updated_at=future_watermark,
            ),
        )

        with pytest.raises(ConcurrentRunError):
            _ = execute_run(
                candidate_profile_id=profile_id,
                watermarks_repo=workflow,
                jobs_repo=jobs,
                audit_repo=audit,
                mcp_source=_StubMcpSource(),
                renderer=_StubRenderer(),
                notifier=_StubNotifier(),
                clock=_FixedClock(clock_now),
            )

    def test_no_watermark_allows_run(
        self, tmp_path: Path,
    ) -> None:
        """No existing watermark must allow a new run."""
        clock_now = datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC)

        workflow, jobs, audit = _bootstrap_all(tmp_path)
        profile_id = CandidateProfileId("profile-no-watermark")
        _ = workflow.upsert_candidate_profile(
            CandidateProfileRecord(
                profile_id=profile_id,
                candidate_id=CandidateId("candidate-no-wm"),
                active_version=CandidateProfileVersionId("v1"),
                timezone_name="UTC",
                created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ),
        )

        result = execute_run(
            candidate_profile_id=profile_id,
            watermarks_repo=workflow,
            jobs_repo=jobs,
            audit_repo=audit,
            mcp_source=_StubMcpSource(),
            renderer=_StubRenderer(),
            notifier=_StubNotifier(),
            clock=_FixedClock(clock_now),
        )

        assert result.jobs_discovered == 0
        assert result.completed_at == clock_now
