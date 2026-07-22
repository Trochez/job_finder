"""Workflow state transitions with kill-switch and legal transition validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Final, override
from uuid import uuid4

from job_finder.adapters.repositories.workflow import (
    StoredWorkflowTransition,
    WorkflowTransitionAppend,
)
from job_finder.domain.ids import JobId, RunId
from job_finder.domain.states import WorkflowState

if TYPE_CHECKING:
    from job_finder.adapters.repositories.workflow import (
        SqliteWorkflowRepository,
    )


# ── Legal state-transition map ─────────────────────────────────────────────

NoneState = type(None)  # Sentinel type representing the initial (null) state.

LEGAL_TRANSITIONS: Final[
    dict[tuple[WorkflowState | None, WorkflowState], str]
] = {
    (None, WorkflowState.EVALUATED): "initial job evaluation",
    (
        WorkflowState.EVALUATED,
        WorkflowState.INELIGIBLE,
    ): "hard filter or below threshold",
    (
        WorkflowState.EVALUATED,
        WorkflowState.READY_FOR_USER,
    ): "eligible and meets threshold",
    (
        WorkflowState.READY_FOR_USER,
        WorkflowState.SUBMITTED,
    ): "user submitted application",
    (
        WorkflowState.READY_FOR_USER,
        WorkflowState.CANCELLED,
    ): "user cancelled",
    (
        WorkflowState.READY_FOR_USER,
        WorkflowState.HUMAN_CHECKPOINT_PAUSE,
    ): "checkpoint blocked",
    (
        WorkflowState.HUMAN_CHECKPOINT_PAUSE,
        WorkflowState.READY_FOR_USER,
    ): "checkpoint resolved",
    (
        WorkflowState.HUMAN_CHECKPOINT_PAUSE,
        WorkflowState.CANCELLED,
    ): "user gave up",
    (
        WorkflowState.SUBMITTED,
        WorkflowState.FAILED,
    ): "submission failed",
    (
        WorkflowState.SUBMITTED,
        WorkflowState.HUMAN_CHECKPOINT_PAUSE,
    ): "submission checkpoint blocked",
    (
        WorkflowState.HUMAN_CHECKPOINT_PAUSE,
        WorkflowState.FAILED,
    ): "checkpoint timeout or error",
    (
        WorkflowState.EVALUATED,
        WorkflowState.FAILED,
    ): "evaluation failure",
    (
        WorkflowState.READY_FOR_USER,
        WorkflowState.FAILED,
    ): "unrecoverable error",
    (
        WorkflowState.FAILED,
        WorkflowState.CANCELLED,
    ): "cleanup after failure",
}

# Transitions always allowed when the kill switch is active.
_KILL_SWITCH_ALLOWED: Final[frozenset[WorkflowState]] = frozenset(
    {WorkflowState.CANCELLED, WorkflowState.FAILED},
)


@dataclass(frozen=True, slots=True)
class KillSwitch:
    """A kill switch that halts active workflow transitions.

    When *is_active* is ``True``, ``advance_workflow`` raises
    ``KillSwitchEngagedError`` for most transitions, effectively freezing
    the workflow until the operator disengages the switch.
    """

    is_active: bool


@dataclass(frozen=True, slots=True)
class KillSwitchEngagedError(Exception):
    """Raised when a workflow transition is denied by an active kill switch."""

    job_id: JobId
    from_state: WorkflowState | None
    to_state: WorkflowState

    @override
    def __str__(self) -> str:
        return (
            f"kill switch is active - cannot transition "
            f"{self.job_id} from {self.from_state} to {self.to_state}"
        )


@dataclass(frozen=True, slots=True)
class IllegalTransitionError(Exception):
    """Raised when a workflow transition is not in the legal map."""

    job_id: JobId
    from_state: WorkflowState | None
    to_state: WorkflowState

    @override
    def __str__(self) -> str:
        return (
            f"illegal transition for {self.job_id}: "
            f"{self.from_state} -> {self.to_state}"
        )


def _uuid4() -> str:
    return str(uuid4())


def advance_workflow(  # noqa: PLR0913
    *,
    job_id: JobId,
    from_state: WorkflowState | None,
    to_state: WorkflowState,
    workflow_repo: SqliteWorkflowRepository,
    kill_switch: KillSwitch,
    run_id: RunId | None = None,
    occurred_at: datetime | None = None,
    transition_id: str | None = None,
) -> StoredWorkflowTransition:
    """Advance a job's workflow state through a legal transition.

    Validates that the transition is legal, checks the kill switch, and
    persists the transition via *workflow_repo*.  When the kill switch is
    active, only transitions to ``CANCELLED`` or ``FAILED`` are permitted.

    Parameters
    ----------
    job_id:
        The job to transition.
    from_state:
        The expected current state (``None`` for the initial transition).
    to_state:
        The target state.
    workflow_repo:
        Repository for persisting the transition.
    kill_switch:
        Kill switch that may block the transition.
    run_id:
        Optional run identifier.  Auto-generated when omitted.
    occurred_at:
        Optional timestamp.  Uses the current UTC time when omitted.
    transition_id:
        Optional explicit transition identifier.  Auto-generated when omitted.

    Returns:
    -------
    The persisted ``StoredWorkflowTransition`` record.

    Raises:
    ------
    KillSwitchEngagedError
        The kill switch is active and the transition is not to ``CANCELLED``
        or ``FAILED``.
    IllegalTransitionError
        The (from, to) pair is not in the legal transition map.
    WorkflowTransitionConflictError
        The repository detected a state conflict (e.g. unexpected from_state).
    """
    _validate_legal(from_state=from_state, to_state=to_state, job_id=job_id)
    _validate_kill_switch(
        kill_switch=kill_switch,
        from_state=from_state,
        to_state=to_state,
        job_id=job_id,
    )

    resolved_run_id = run_id or RunId(f"run:{_uuid4()}")
    resolved_occurred_at = occurred_at or datetime.now(tz=UTC)
    resolved_transition_id = transition_id or f"tr:{_uuid4()}"
    sequence_number = _next_sequence(job_id=job_id, workflow_repo=workflow_repo)

    transition = WorkflowTransitionAppend(
        transition_id=resolved_transition_id,
        job_id=job_id,
        run_id=resolved_run_id,
        sequence_number=sequence_number,
        from_state=from_state,
        to_state=to_state,
        occurred_at=resolved_occurred_at,
    )
    return workflow_repo.append_transition(transition)


def _validate_legal(
    *,
    from_state: WorkflowState | None,
    to_state: WorkflowState,
    job_id: JobId,
) -> None:
    key = (from_state, to_state)
    if key not in LEGAL_TRANSITIONS:
        raise IllegalTransitionError(
            job_id=job_id,
            from_state=from_state,
            to_state=to_state,
        )


def _validate_kill_switch(
    *,
    kill_switch: KillSwitch,
    from_state: WorkflowState | None,
    to_state: WorkflowState,
    job_id: JobId,
) -> None:
    if not kill_switch.is_active:
        return
    if to_state in _KILL_SWITCH_ALLOWED:
        return
    raise KillSwitchEngagedError(
        job_id=job_id,
        from_state=from_state,
        to_state=to_state,
    )


def _next_sequence(
    *,
    job_id: JobId,
    workflow_repo: SqliteWorkflowRepository,
) -> int:
    existing = workflow_repo.list_transitions(job_id)
    return len(existing) + 1
