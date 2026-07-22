from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path for module resolution
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

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
from job_finder.application.retention import purge_aged_audit_data
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
    import sqlite3


def _require_verified_identity(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> CanonicalJobIdentity:
    match identity_result:
        case CanonicalJobIdentity() as identity:
            return identity
        case IdentityUnverified() as unexpected:
            msg = f"expected a verified identity, got {unexpected.audit_status}"
            raise AssertionError(msg)


def _bootstrap_all(
    tmp_path: Path,
) -> tuple[
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


def test_audit_retention_day_90_minus_one_survives(tmp_path: Path) -> None:
    """A record at day 90 - 1 (89 days old) must survive the purge."""
    # Given
    reference = datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)
    connection, workflow, jobs, audit = _bootstrap_all(tmp_path)
    observed_at = reference - timedelta(days=365)
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
            external_job_id=" LI-456 ",
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

    young_evaluation = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)  # ~1 day old
    entry = EvaluationAuditEntry(
        entry_id="audit-young",
        job_id=job.job_id,
        run_id=RunId("run-1"),
        decision=EligibilityDecision.ELIGIBLE,
        applied_threshold=60,
        score_value=85,
        scoring_policy_version="2026-07-fixed-30-30-25-10-5",
        factor_breakdown_json="{}",
        evidence_references="src::fact-1",
        cv_artifact_reference=None,
        evaluated_at_utc=young_evaluation,
    )
    audit.append_evaluation(entry)

    cutoff = reference - timedelta(days=90)

    # When
    purged = purge_aged_audit_data(connection, cutoff)

    # Then
    assert purged == 0
    survivors = audit.list_for_job(job.job_id)
    assert len(survivors) == 1


def test_audit_retention_day_90_plus_one_purges_and_leaves_tombstone(
    tmp_path: Path,
) -> None:
    """A record at day 90 + 1 must be purged; the tombstone must remain."""
    # Given
    reference = datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)
    connection, workflow, jobs, audit = _bootstrap_all(tmp_path)
    observed_at = reference - timedelta(days=365)
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
            external_job_id=" LI-789 ",
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

    old_evaluation = reference - timedelta(days=91)
    entry = EvaluationAuditEntry(
        entry_id="audit-old",
        job_id=job.job_id,
        run_id=RunId("run-1"),
        decision=EligibilityDecision.INELIGIBLE,
        applied_threshold=None,
        score_value=None,
        scoring_policy_version="2026-07-fixed-30-30-25-10-5",
        factor_breakdown_json="{}",
        evidence_references="",
        cv_artifact_reference=None,
        evaluated_at_utc=old_evaluation,
    )
    audit.append_evaluation(entry)

    cutoff = reference - timedelta(days=90)

    # When
    purged = purge_aged_audit_data(connection, cutoff)

    # Then
    assert purged == 1
    assert audit.list_for_job(job.job_id) == ()

    # Tombstone must remain
    tombstones = connection.execute(
        "SELECT identity_hash, reason FROM submission_tombstones"
    ).fetchall()
    assert len(tombstones) == 1
    tombstone = tombstones[0]
    assert tombstone["identity_hash"] == identity.identity_hash
    assert tombstone["reason"] == "audit_retention_purge"
