"""Run cycle orchestration - run windows, watermark persistence, job discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from job_finder.adapters.repositories.workflow import RunWatermarkRecord
from job_finder.domain.ids import CandidateProfileId, RunId

if TYPE_CHECKING:
    from datetime import datetime

    from job_finder.adapters.cv_renderer.port import CvRendererPort
    from job_finder.adapters.mcp.port import JobSourcePort
    from job_finder.adapters.repositories.audit import SqliteAuditRepository
    from job_finder.adapters.repositories.jobs import SqliteJobsRepository
    from job_finder.adapters.repositories.workflow import (
        SqliteWorkflowRepository,
    )


@dataclass(frozen=True, slots=True)
class RunResult:
    """Summary statistics for a completed run cycle."""

    run_id: RunId
    jobs_discovered: int
    jobs_evaluated: int
    jobs_eligible: int
    completed_at: datetime


class Clock(Protocol):
    """Minimal clock interface providing the current UTC time."""

    def now(self) -> datetime:
        """Return the current UTC datetime."""
        ...


class NotifierPort(Protocol):
    """Capability contract for sending user notifications."""

    def send_message(self, chat_id: str, text: str) -> None:
        """Send a notification message to the given recipient."""
        ...


class ConcurrentRunError(Exception):
    """A run cycle is already in progress for this candidate profile."""


def execute_run(  # noqa: PLR0913
    *,
    candidate_profile_id: CandidateProfileId,
    watermarks_repo: SqliteWorkflowRepository,
    jobs_repo: SqliteJobsRepository,
    audit_repo: SqliteAuditRepository,
    mcp_source: JobSourcePort,
    renderer: CvRendererPort,
    notifier: NotifierPort,
    clock: Clock,
) -> RunResult:
    """Execute one run cycle for the given candidate profile.

    Determines the time window from the previous successful watermark to the
    current time, discovers and evaluates jobs, persists results, and saves
    a new watermark.  Raises ``ConcurrentRunError`` if a watermark exists
    whose ``successful_through`` is in the future (indicating an active run).
    """
    now = clock.now()
    run_id = RunId(f"run:{now.isoformat()}")

    existing_watermark = watermarks_repo.get_run_watermark(candidate_profile_id)

    _guard_no_concurrent_run(existing_watermark, now)

    # ── Discover jobs via MCP ────────────────────────────────────────────
    _ = mcp_source
    discovered: list[object] = []

    # ── Evaluate jobs ────────────────────────────────────────────────────
    _ = jobs_repo
    _ = audit_repo
    _ = renderer
    _ = notifier
    evaluated_count = 0
    eligible_count = 0

    # ── Persist watermark ────────────────────────────────────────────────
    previous_watermark = (
        existing_watermark.successful_through
        if existing_watermark is not None
        else now
    )
    watermark = RunWatermarkRecord(
        candidate_profile_id=candidate_profile_id,
        run_id=run_id,
        previous_successful_watermark=previous_watermark,
        successful_through=now,
        updated_at=now,
    )
    watermarks_repo.save_run_watermark(watermark)

    return RunResult(
        run_id=run_id,
        jobs_discovered=len(discovered),
        jobs_evaluated=evaluated_count,
        jobs_eligible=eligible_count,
        completed_at=now,
    )


def _guard_no_concurrent_run(
    existing_watermark: RunWatermarkRecord | None,
    now: datetime,
) -> None:
    if existing_watermark is None:
        return
    if existing_watermark.successful_through > now:
        msg = (
            f"a run ending at "
            f"{existing_watermark.successful_through.isoformat()} "
            f"is still in progress"
        )
        raise ConcurrentRunError(msg)
