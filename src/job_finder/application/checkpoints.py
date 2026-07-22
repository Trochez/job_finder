"""Screening answer management and checkpoint pause orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, override
from uuid import uuid4

from job_finder.adapters.repositories.workflow import (
    StoredWorkflowTransition,
    WorkflowTransitionAppend,
)
from job_finder.domain.ids import JobId, RunId
from job_finder.domain.states import CheckpointState, WorkflowState

if TYPE_CHECKING:
    from job_finder.adapters.repositories.workflow import (
        SqliteWorkflowRepository,
    )


@dataclass(frozen=True, slots=True)
class ScreeningAnswer:
    """An exact-match screening question answer for a job application."""

    question_key: str
    answer: str


@dataclass(frozen=True, slots=True)
class PauseResult:
    """Outcome of pausing a workflow for a checkpoint."""

    transition: StoredWorkflowTransition
    checkpoint_state: CheckpointState
    detail: str


@dataclass(frozen=True, slots=True)
class CheckpointPauseError(Exception):
    """Raised when a checkpoint pause cannot be created."""

    job_id: JobId
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.job_id}: {self.detail}"


def get_answer(
    question_key: str,
    saved_answers: tuple[ScreeningAnswer, ...],
) -> str | None:
    """Retrieve a saved answer by exact question-key match.

    Returns ``None`` when no answer exists for the given key.
    """
    for saved in saved_answers:
        if saved.question_key == question_key:
            return saved.answer
    return None


def _uuid4() -> str:
    return str(uuid4())


def pause_for_checkpoint(  # noqa: PLR0913
    *,
    checkpoint_state: CheckpointState,
    job_id: JobId,
    detail: str,
    workflow_repo: SqliteWorkflowRepository,
    run_id: RunId | None = None,
    occurred_at: datetime | None = None,
) -> PauseResult:
    """Pause the workflow for a human to resolve a checkpoint.

    Determines the current workflow state for *job_id* and appends a
    transition to ``HUMAN_CHECKPOINT_PAUSE``.  The previous workflow state
    is recorded so the workflow can be resumed later.

    Parameters
    ----------
    checkpoint_state:
        The kind of checkpoint that blocked the workflow.
    job_id:
        The job whose workflow is being paused.
    detail:
        Human-readable detail about the checkpoint (e.g. the captcha URL
        or the screening question text).
    workflow_repo:
        Repository for reading and persisting workflow state.
    run_id:
        Optional run identifier.  Auto-generated when omitted.
    occurred_at:
        Optional timestamp.  Uses the current UTC time when omitted.

    Returns:
    -------
    A ``PauseResult`` containing the persisted transition.

    Raises:
    ------
    WorkflowTransitionConflictError
        The current workflow state could not transition to the pause state.
    """
    resolved_run_id = run_id or RunId(f"run:{_uuid4()}")
    resolved_occurred_at = occurred_at or datetime.now(tz=UTC)
    resolved_transition_id = f"cp:{_uuid4()}"

    # Read current state via list_transitions to determine from_state
    existing = workflow_repo.list_transitions(job_id)
    current_state: WorkflowState | None = existing[-1].to_state if existing else None

    existing_seq = len(existing)

    transition = WorkflowTransitionAppend(
        transition_id=resolved_transition_id,
        job_id=job_id,
        run_id=resolved_run_id,
        sequence_number=existing_seq + 1,
        from_state=current_state,
        to_state=WorkflowState.HUMAN_CHECKPOINT_PAUSE,
        occurred_at=resolved_occurred_at,
    )
    stored = workflow_repo.append_transition(transition)

    return PauseResult(
        transition=stored,
        checkpoint_state=checkpoint_state,
        detail=detail,
    )
