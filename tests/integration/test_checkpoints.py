"""Integration tests for checkpoint pause behaviour with a real SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from job_finder.adapters.db import bootstrap_private_sqlite_storage
from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.adapters.repositories.jobs import (
    CanonicalJobUpsert,
    SqliteJobsRepository,
)
from job_finder.adapters.repositories.workflow import (
    CandidateProfileRecord,
    SqliteWorkflowRepository,
    WorkflowTransitionAppend,
    WorkflowTransitionConflictError,
)
from job_finder.adapters.settings import PrivateSettings
from job_finder.application.checkpoints import (
    PauseResult,
    pause_for_checkpoint,
)
from job_finder.domain.ids import (
    CandidateId,
    CandidateProfileId,
    CandidateProfileVersionId,
    JobId,
    RunId,
)
from job_finder.domain.job_identity import (
    CanonicalJobIdentity,
    IdentityUnverified,
    build_job_identity,
)
from job_finder.domain.states import CheckpointState, WorkflowState

if TYPE_CHECKING:
    from pathlib import Path


def _require_verified(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> CanonicalJobIdentity:
    match identity_result:
        case CanonicalJobIdentity() as identity:
            return identity
        case IdentityUnverified() as unexpected:
            msg = f"expected a verified identity, got {unexpected.audit_status}"
            raise AssertionError(msg)


def _bootstrap_with_job_at_state(
    tmp_path: Path,
    current_state: WorkflowState,
) -> tuple[SqliteWorkflowRepository, SqliteJobsRepository, JobId]:
    settings = PrivateSettings.from_paths(app_data_dir=tmp_path / "private")
    storage = bootstrap_private_sqlite_storage(settings)
    connection = connect_migrated_sqlite_database(storage.database_path)
    workflow = SqliteWorkflowRepository(connection)
    jobs = SqliteJobsRepository(connection)

    observed_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    profile = workflow.upsert_candidate_profile(
        CandidateProfileRecord(
            profile_id=CandidateProfileId("profile-cp"),
            candidate_id=CandidateId("candidate-cp"),
            active_version=CandidateProfileVersionId("v1"),
            timezone_name="UTC",
            created_at=observed_at,
        ),
    )
    identity = _require_verified(
        build_job_identity(
            source="linkedin",
            external_job_id=" CP-001 ",
            canonical_company_key="acme-inc",
        ),
    )
    job = jobs.upsert_canonical_job(
        CanonicalJobUpsert(
            candidate_profile_id=profile.profile_id,
            identity=identity,
            discovered_at=observed_at,
        ),
    )

    # Build transition sequence to reach current_state
    states_sequence = _state_path(current_state)
    for idx, (from_s, to_s) in enumerate(states_sequence):
        _ = workflow.append_transition(
            WorkflowTransitionAppend(
                transition_id=f"tr-{idx}",
                job_id=job.job_id,
                run_id=RunId("run-cp"),
                sequence_number=idx + 1,
                from_state=from_s,
                to_state=to_s,
                occurred_at=observed_at,
            ),
        )

    return workflow, jobs, job.job_id


def _state_path(
    target: WorkflowState,
) -> list[tuple[WorkflowState | None, WorkflowState]]:
    """Return the transition sequence to reach *target* from None."""
    paths: dict[WorkflowState, list[tuple[WorkflowState | None, WorkflowState]]] = {
        WorkflowState.EVALUATED: [(None, WorkflowState.EVALUATED)],
        WorkflowState.READY_FOR_USER: [
            (None, WorkflowState.EVALUATED),
            (WorkflowState.EVALUATED, WorkflowState.READY_FOR_USER),
        ],
        WorkflowState.SUBMITTED: [
            (None, WorkflowState.EVALUATED),
            (WorkflowState.EVALUATED, WorkflowState.READY_FOR_USER),
            (WorkflowState.READY_FOR_USER, WorkflowState.SUBMITTED),
        ],
    }
    result = paths.get(target)
    if result is None:
        msg = f"no predefined path for {target}"
        raise ValueError(msg)
    return result


class TestPauseForCheckpoint:
    """Checkpoint pause creation and state recording."""

    def test_pause_from_ready_for_user_persists_transition(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap_with_job_at_state(
            tmp_path, WorkflowState.READY_FOR_USER,
        )
        occurred_at = datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)

        result = pause_for_checkpoint(
            checkpoint_state=CheckpointState.CAPTCHA,
            job_id=job_id,
            detail="Captcha at https://example.com/captcha",
            workflow_repo=workflow,
            occurred_at=occurred_at,
        )

        assert isinstance(result, PauseResult)
        assert result.checkpoint_state is CheckpointState.CAPTCHA
        assert result.detail == "Captcha at https://example.com/captcha"
        assert result.transition.to_state is WorkflowState.HUMAN_CHECKPOINT_PAUSE

    def test_pause_from_submitted_persists_transition(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap_with_job_at_state(
            tmp_path, WorkflowState.SUBMITTED,
        )
        occurred_at = datetime(2026, 1, 2, 11, 0, 0, tzinfo=UTC)

        result = pause_for_checkpoint(
            checkpoint_state=CheckpointState.TWO_FACTOR,
            job_id=job_id,
            detail="2FA code required",
            workflow_repo=workflow,
            occurred_at=occurred_at,
        )

        assert result.checkpoint_state is CheckpointState.TWO_FACTOR
        assert result.transition.to_state is WorkflowState.HUMAN_CHECKPOINT_PAUSE

    def test_pause_creates_sequential_transition(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap_with_job_at_state(
            tmp_path, WorkflowState.READY_FOR_USER,
        )
        occurred_at = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)

        result = pause_for_checkpoint(
            checkpoint_state=CheckpointState.ANTI_AUTOMATION,
            job_id=job_id,
            detail="Anti-automation detected",
            workflow_repo=workflow,
            occurred_at=occurred_at,
        )

        transitions = workflow.list_transitions(job_id)
        # The pause is the last transition
        assert transitions[-1].transition_id == result.transition.transition_id
        assert transitions[-1].to_state is WorkflowState.HUMAN_CHECKPOINT_PAUSE

    def test_all_checkpoint_states_are_accepted(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap_with_job_at_state(
            tmp_path, WorkflowState.READY_FOR_USER,
        )
        occurred_at = datetime(2026, 1, 2, 13, 0, 0, tzinfo=UTC)

        for cp_state in CheckpointState:
            result = pause_for_checkpoint(
                checkpoint_state=cp_state,
                job_id=job_id,
                detail=f"Blocked by {cp_state.tag}",
                workflow_repo=workflow,
                occurred_at=occurred_at,
            )
            assert result.checkpoint_state is cp_state

    def test_pause_on_missing_job_raises_error(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, _job_id = _bootstrap_with_job_at_state(
            tmp_path, WorkflowState.READY_FOR_USER,
        )
        occurred_at = datetime(2026, 1, 2, 14, 0, 0, tzinfo=UTC)

        with pytest.raises(WorkflowTransitionConflictError):
            _ = pause_for_checkpoint(
                checkpoint_state=CheckpointState.LOGIN_CHALLENGE,
                job_id=JobId("job:nonexistent"),
                detail="Login challenge",
                workflow_repo=workflow,
                occurred_at=occurred_at,
            )

    def test_pause_result_includes_correct_detail(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap_with_job_at_state(
            tmp_path, WorkflowState.READY_FOR_USER,
        )
        occurred_at = datetime(2026, 1, 2, 15, 0, 0, tzinfo=UTC)

        result = pause_for_checkpoint(
            checkpoint_state=CheckpointState.UNKNOWN_SCREENING_QUESTION,
            job_id=job_id,
            detail="Unknown question: 'What is your pet's name?'",
            workflow_repo=workflow,
            occurred_at=occurred_at,
        )

        assert result.detail == "Unknown question: 'What is your pet's name?'"
