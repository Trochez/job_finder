"""Integration tests for kill-switch behaviour with a real SQLite database."""

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
)
from job_finder.adapters.settings import PrivateSettings
from job_finder.application.workflow import (
    KillSwitch,
    KillSwitchEngagedError,
    advance_workflow,
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
from job_finder.domain.states import WorkflowState

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


def _bootstrap(
    tmp_path: Path,
) -> tuple[SqliteWorkflowRepository, SqliteJobsRepository, JobId]:
    settings = PrivateSettings.from_paths(app_data_dir=tmp_path / "private")
    storage = bootstrap_private_sqlite_storage(settings)
    connection = connect_migrated_sqlite_database(storage.database_path)
    workflow = SqliteWorkflowRepository(connection)
    jobs = SqliteJobsRepository(connection)

    observed_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    profile = workflow.upsert_candidate_profile(
        CandidateProfileRecord(
            profile_id=CandidateProfileId("profile-ks"),
            candidate_id=CandidateId("candidate-ks"),
            active_version=CandidateProfileVersionId("v1"),
            timezone_name="UTC",
            created_at=observed_at,
        ),
    )
    identity = _require_verified(
        build_job_identity(
            source="linkedin",
            external_job_id=" KS-001 ",
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

    # Initial transition: None -> EVALUATED
    _ = workflow.append_transition(
        WorkflowTransitionAppend(
            transition_id="tr-initial",
            job_id=job.job_id,
            run_id=RunId("run-ks"),
            sequence_number=1,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            occurred_at=observed_at,
        ),
    )
    return workflow, jobs, job.job_id


class TestKillSwitchIntegration:
    """Kill switch behaviour against a real database."""

    def test_inactive_kill_switch_allows_normal_advance(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap(tmp_path)
        kill_switch = KillSwitch(is_active=False)
        occurred_at = datetime(2026, 1, 2, 4, 0, 0, tzinfo=UTC)

        transition = advance_workflow(
            job_id=job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.READY_FOR_USER,
            workflow_repo=workflow,
            kill_switch=kill_switch,
            occurred_at=occurred_at,
        )

        assert transition.to_state is WorkflowState.READY_FOR_USER
        assert transition.from_state is WorkflowState.EVALUATED

    def test_active_kill_switch_blocks_transition(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap(tmp_path)
        kill_switch = KillSwitch(is_active=True)
        occurred_at = datetime(2026, 1, 2, 5, 0, 0, tzinfo=UTC)

        with pytest.raises(KillSwitchEngagedError):
            _ = advance_workflow(
                job_id=job_id,
                from_state=WorkflowState.EVALUATED,
                to_state=WorkflowState.READY_FOR_USER,
                workflow_repo=workflow,
                kill_switch=kill_switch,
                occurred_at=occurred_at,
            )

    def test_active_kill_switch_allows_failed(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap(tmp_path)
        kill_switch = KillSwitch(is_active=True)
        occurred_at = datetime(2026, 1, 2, 6, 0, 0, tzinfo=UTC)

        transition = advance_workflow(
            job_id=job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.FAILED,
            workflow_repo=workflow,
            kill_switch=kill_switch,
            occurred_at=occurred_at,
        )

        assert transition.to_state is WorkflowState.FAILED

    def test_transition_persists_after_advance(
        self, tmp_path: Path,
    ) -> None:
        workflow, _jobs, job_id = _bootstrap(tmp_path)
        kill_switch = KillSwitch(is_active=False)
        occurred_at = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)

        _ = advance_workflow(
            job_id=job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.READY_FOR_USER,
            workflow_repo=workflow,
            kill_switch=kill_switch,
            occurred_at=occurred_at,
        )

        transitions = workflow.list_transitions(job_id)
        assert len(transitions) == 2  # initial + this one
        assert transitions[-1].to_state is WorkflowState.READY_FOR_USER
