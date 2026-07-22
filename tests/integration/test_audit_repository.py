from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from job_finder.adapters.db import bootstrap_private_sqlite_storage
from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.adapters.repositories.audit import (
    EvaluationAuditEntry,
    SqliteAuditRepository,
)
from job_finder.adapters.repositories.jobs import (
    CanonicalJobUpsert,
    SqliteJobsRepository,
)
from job_finder.adapters.repositories.workflow import (
    CandidateProfileRecord,
    SqliteWorkflowRepository,
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
from job_finder.domain.states import EligibilityDecision

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


def _bootstrap_all(tmp_path: Path) -> tuple[
    sqlite3.Connection,
    SqliteWorkflowRepository,
    SqliteJobsRepository,
    SqliteAuditRepository,
]:
    settings = PrivateSettings.from_paths(app_data_dir=tmp_path / "private")
    storage = bootstrap_private_sqlite_storage(settings)
    connection = connect_migrated_sqlite_database(storage.database_path)
    return (
        connection,
        SqliteWorkflowRepository(connection),
        SqliteJobsRepository(connection),
        SqliteAuditRepository(connection),
    )


def test_append_writes_decision_evidence_and_artifact_trail(tmp_path: Path) -> None:
    # Given
    _connection, workflow, jobs, audit = _bootstrap_all(tmp_path)
    observed_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    profile = workflow.upsert_candidate_profile(
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
    job = jobs.upsert_canonical_job(
        CanonicalJobUpsert(
            candidate_profile_id=profile.profile_id,
            identity=identity,
            discovered_at=observed_at,
        )
    )

    entry = EvaluationAuditEntry(
        entry_id="audit-1",
        job_id=job.job_id,
        run_id=RunId("run-1"),
        decision=EligibilityDecision.ELIGIBLE,
        applied_threshold=60,
        score_value=85,
        scoring_policy_version="2026-07-fixed-30-30-25-10-5",
        factor_breakdown_json='{"role_alignment": 80, "skills_tools": 90}',
        evidence_references="src::fact-1,src::fact-2",
        cv_artifact_reference=str(tmp_path / "cv-v1.pdf"),
        evaluated_at_utc=observed_at,
    )

    # When
    audit.append_evaluation(entry)

    # Then
    entries = audit.list_for_job(job.job_id)
    assert len(entries) == 1
    stored = entries[0]
    assert stored.entry_id == "audit-1"
    assert stored.job_id == job.job_id
    assert stored.run_id == RunId("run-1")
    assert stored.decision is EligibilityDecision.ELIGIBLE
    assert stored.applied_threshold == 60
    assert stored.score_value == 85
    assert stored.scoring_policy_version == "2026-07-fixed-30-30-25-10-5"
    assert stored.factor_breakdown_json == '{"role_alignment": 80, "skills_tools": 90}'
    assert stored.evidence_references == "src::fact-1,src::fact-2"
    assert stored.cv_artifact_reference == str(tmp_path / "cv-v1.pdf")
    assert stored.evaluated_at_utc == observed_at


def test_injected_error_rolls_back_the_new_decision(tmp_path: Path) -> None:
    # Given
    _connection, workflow, jobs, audit = _bootstrap_all(tmp_path)
    observed_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    profile = workflow.upsert_candidate_profile(
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
    job = jobs.upsert_canonical_job(
        CanonicalJobUpsert(
            candidate_profile_id=profile.profile_id,
            identity=identity,
            discovered_at=observed_at,
        )
    )
    entry = EvaluationAuditEntry(
        entry_id="audit-1",
        job_id=job.job_id,
        run_id=RunId("run-1"),
        decision=EligibilityDecision.ELIGIBLE,
        applied_threshold=60,
        score_value=85,
        scoring_policy_version="2026-07-fixed-30-30-25-10-5",
        factor_breakdown_json="{}",
        evidence_references="",
        cv_artifact_reference=None,
        evaluated_at_utc=observed_at,
    )
    audit.append_evaluation(entry)

    # When - try to append a different entry with the same PK
    duplicate = EvaluationAuditEntry(
        entry_id="audit-1",
        job_id=job.job_id,
        run_id=RunId("run-1"),
        decision=EligibilityDecision.HARD_FILTER_BLOCKED,
        applied_threshold=None,
        score_value=None,
        scoring_policy_version="2026-07-fixed-30-30-25-10-5",
        factor_breakdown_json="{}",
        evidence_references="",
        cv_artifact_reference=None,
        evaluated_at_utc=observed_at,
    )
    with pytest.raises(sqlite3.IntegrityError):
        audit.append_evaluation(duplicate)

    # Then - original entry is preserved, no partial record
    entries = audit.list_for_job(job.job_id)
    assert len(entries) == 1
    assert entries[0].decision is EligibilityDecision.ELIGIBLE
