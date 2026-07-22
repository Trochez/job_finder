from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from job_finder.adapters.db import bootstrap_private_sqlite_storage
from job_finder.adapters.repositories.jobs import (
    CanonicalJobUpsert,
    IdentityUnverifiedInsert,
    SqliteJobsRepository,
)
from job_finder.adapters.repositories.workflow import (
    CandidateProfileRecord,
    RunWatermarkRecord,
    SqliteWorkflowRepository,
    WorkflowTransitionAppend,
    WorkflowTransitionConflictError,
)
from job_finder.adapters.settings import PrivateSettings
from job_finder.domain.ids import (
    CandidateId,
    CandidateProfileId,
    CandidateProfileVersionId,
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


def _require_verified_identity(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> CanonicalJobIdentity:
    match identity_result:
        case CanonicalJobIdentity() as identity:
            return identity
        case IdentityUnverified() as unexpected:
            msg = f"expected a verified identity, got {unexpected.audit_status}"
            raise AssertionError(msg)


def _require_unverified_identity(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> IdentityUnverified:
    match identity_result:
        case IdentityUnverified() as unverified:
            return unverified
        case CanonicalJobIdentity() as unexpected:
            msg = f"expected identity_unverified, got {unexpected.identity_hash}"
            raise AssertionError(msg)


def _bootstrap_repositories(
    tmp_path: Path,
) -> tuple[SqliteJobsRepository, SqliteWorkflowRepository]:
    settings = PrivateSettings.from_paths(app_data_dir=tmp_path / "private")
    storage = bootstrap_private_sqlite_storage(settings)
    return (
        SqliteJobsRepository.connect(storage.database_path),
        SqliteWorkflowRepository.connect(storage.database_path),
    )


def test_migrations_persist_canonical_jobs_watermarks_and_immutable_transitions(
    tmp_path: Path,
) -> None:
    # Given
    jobs_repository, workflow_repository = _bootstrap_repositories(tmp_path)
    observed_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    successful_through = datetime(2026, 1, 2, 6, 0, 0, tzinfo=UTC)
    profile = workflow_repository.upsert_candidate_profile(
        CandidateProfileRecord(
            profile_id=CandidateProfileId("profile-1"),
            candidate_id=CandidateId("candidate-1"),
            active_version=CandidateProfileVersionId("v1"),
            timezone_name="UTC",
            created_at=observed_at,
        )
    )
    identity = _require_verified_identity(
        build_job_identity(
            source="linkedin",
            external_job_id=" LI-123 ",
            canonical_company_key="acme-inc",
        )
    )

    # When
    first_job = jobs_repository.upsert_canonical_job(
        CanonicalJobUpsert(
            candidate_profile_id=profile.profile_id,
            identity=identity,
            discovered_at=observed_at,
        )
    )
    duplicate_job = jobs_repository.upsert_canonical_job(
        CanonicalJobUpsert(
            candidate_profile_id=profile.profile_id,
            identity=identity,
            discovered_at=observed_at,
        )
    )
    workflow_repository.save_run_watermark(
        RunWatermarkRecord(
            candidate_profile_id=profile.profile_id,
            run_id=RunId("run-1"),
            previous_successful_watermark=observed_at,
            successful_through=successful_through,
            updated_at=successful_through,
        )
    )
    recorded_transition = workflow_repository.append_transition(
        WorkflowTransitionAppend(
            transition_id="transition-1",
            job_id=first_job.job_id,
            run_id=RunId("run-1"),
            sequence_number=1,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            occurred_at=observed_at,
        )
    )

    with pytest.raises(WorkflowTransitionConflictError):
        _ = workflow_repository.append_transition(
            WorkflowTransitionAppend(
                transition_id="transition-2",
                job_id=first_job.job_id,
                run_id=RunId("run-1"),
                sequence_number=1,
                from_state=WorkflowState.EVALUATED,
                to_state=WorkflowState.READY_FOR_USER,
                occurred_at=successful_through,
            )
        )

    # Then
    assert duplicate_job.job_id == first_job.job_id
    assert duplicate_job.identity_hash == identity.identity_hash
    assert workflow_repository.get_run_watermark(profile.profile_id) == (
        RunWatermarkRecord(
            candidate_profile_id=profile.profile_id,
            run_id=RunId("run-1"),
            previous_successful_watermark=observed_at,
            successful_through=successful_through,
            updated_at=successful_through,
        )
    )
    assert workflow_repository.list_transitions(first_job.job_id) == (
        recorded_transition,
    )


def test_identity_unverified_jobs_persist_without_canonical_identity(
    tmp_path: Path,
) -> None:
    # Given
    jobs_repository, workflow_repository = _bootstrap_repositories(tmp_path)
    observed_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    profile = workflow_repository.upsert_candidate_profile(
        CandidateProfileRecord(
            profile_id=CandidateProfileId("profile-1"),
            candidate_id=CandidateId("candidate-1"),
            active_version=CandidateProfileVersionId("v1"),
            timezone_name="UTC",
            created_at=observed_at,
        )
    )
    identity = _require_unverified_identity(
        build_job_identity(
            source="linkedin",
            external_job_id="   ",
            canonical_company_key="acme-inc",
        )
    )

    # When
    stored_job = jobs_repository.insert_identity_unverified_job(
        IdentityUnverifiedInsert(
            candidate_profile_id=profile.profile_id,
            identity=identity,
            discovered_at=observed_at,
        )
    )

    # Then
    assert stored_job.identity_status == "identity_unverified"
    assert stored_job.identity_unverified_reason == identity.reason.tag
    assert stored_job.identity_hash is None
