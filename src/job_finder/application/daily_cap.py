"""Daily application cap accounting and policy enforcement.

Prevents runaway automated submissions by capping the number of
application-attempt events per run at a configurable limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, override

from job_finder.domain.errors import DomainError

if TYPE_CHECKING:
    from job_finder.domain.ids import JobId, RunId


# ── events ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ApplicationAttemptStarted:
    """Emitted when the system begins a real application attempt for a job."""

    run_id: RunId
    job_id: JobId


@dataclass(frozen=True, slots=True)
class CapReached:
    """Emitted once per run when the daily application cap is reached.

    After this event no further ``ApplicationAttemptStarted`` events for the
    same run should be processed — the cap halts all remaining job processing.
    """

    run_id: RunId
    count: int


# ── errors ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class InvalidCapLimitError(DomainError):
    """Raised when a ``DailyCapPolicy`` limit is zero or negative."""

    limit: int

    @override
    def __str__(self) -> str:
        """Return a human-readable error message."""
        return f"daily cap limit must be positive, got {self.limit}"


# ── policy ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DailyCapPolicy:
    """Configuration for the daily application cap.

    Attributes:
        limit: Maximum number of application attempts allowed per run.
            Must be a positive integer.  Defaults to 25.
    """

    limit: int = 25

    def __post_init__(self) -> None:
        """Validate that the cap limit is positive."""
        if self.limit < 1:
            raise InvalidCapLimitError(limit=self.limit)


# ── counter ──────────────────────────────────────────────────────────────────


@dataclass
class CapCounter:
    """Tracks the number of application attempts started per run.

    This counter is intentionally dumb — it stores a flat count per run and
    does not attempt to reconstruct state from the event store.
    """

    _attempts: dict[str, int] = field(default_factory=dict)

    def record(self, event: ApplicationAttemptStarted) -> None:
        """Increment the attempt count for the event's run."""
        self._attempts[event.run_id] = self._attempts.get(event.run_id, 0) + 1

    def count_for(self, run_id: RunId) -> int:
        """Return the current attempt count for *run_id* (0 if none)."""
        return self._attempts.get(run_id, 0)


# ── check ────────────────────────────────────────────────────────────────────


def check_cap(policy: DailyCapPolicy, counter: CapCounter, run_id: RunId) -> bool:
    """Return ``True`` while the cap allows more attempts.

    Returns ``False`` when the number of recorded attempts for *run_id*
    meets or exceeds the policy limit, signalling that the cap has been
    reached and all further job processing for this run should halt.
    """
    return counter.count_for(run_id) < policy.limit
