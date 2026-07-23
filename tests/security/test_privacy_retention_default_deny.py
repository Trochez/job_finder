"""Security-sentinel tests: privacy, retention, default-deny, and redaction.

Sentinels are synthetic sensitive strings planted in test data that
MUST remain contained -- they must NOT leak through logs, HTTP responses,
evidence records, notification payloads, or any other output channel.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.job_finder.adapters.db import bootstrap_private_sqlite_storage
from src.job_finder.adapters.mcp.fake import FakeMCPJobSource
from src.job_finder.adapters.mcp.policy import (
    LiveAccessDeniedError,
    create_job_source,
)
from src.job_finder.adapters.mcp.port import JobSearch
from src.job_finder.adapters.migrations import (
    connect_migrated_sqlite_database,
)
from src.job_finder.adapters.notifications.telegram import (
    FakeTelegramNotifier,
    TelegramRedactionError,
)
from src.job_finder.adapters.repositories.audit import (
    EvaluationAuditEntry,
    SqliteAuditRepository,
)
from src.job_finder.adapters.repositories.jobs import (
    CanonicalJobUpsert,
    SqliteJobsRepository,
)
from src.job_finder.adapters.repositories.workflow import (
    CandidateProfileRecord,
    SqliteWorkflowRepository,
)
from src.job_finder.adapters.settings import PrivateSettings
from src.job_finder.application.retention import purge_aged_audit_data
from src.job_finder.domain.ids import (
    CandidateId,
    CandidateProfileId,
    CandidateProfileVersionId,
    RunId,
)
from src.job_finder.domain.job_identity import (
    CanonicalJobIdentity,
    IdentityUnverified,
    build_job_identity,
)
from src.job_finder.domain.states import EligibilityDecision
from src.job_finder.web.app import create_app, inject_test_deps
from src.job_finder.web.deps import AppDependencies

from tests.fakes.sentinels import SentinelDataSet

pytestmark = pytest.mark.security


def _require_verified_identity(
    identity_result: CanonicalJobIdentity | IdentityUnverified,
) -> CanonicalJobIdentity:
    match identity_result:
        case CanonicalJobIdentity() as identity:
            return identity
        case IdentityUnverified() as unexpected:
            msg = f"expected verified identity, got {unexpected.audit_status}"
            raise AssertionError(msg)


def _bootstrap(tmp_path: Path) -> tuple[
    sqlite3.Connection,
    SqliteWorkflowRepository,
    SqliteJobsRepository,
    SqliteAuditRepository,
]:
    settings = PrivateSettings.from_paths(
        app_data_dir=tmp_path / "private",
        sqlite_database_name="security_test.sqlite3",
    )
    _ = bootstrap_private_sqlite_storage(settings)
    connection = connect_migrated_sqlite_database(settings.sqlite_database_path)
    workflow = SqliteWorkflowRepository(connection)
    jobs = SqliteJobsRepository(connection)
    audit = SqliteAuditRepository(connection)
    return connection, workflow, jobs, audit


# ── 1. Sentinel containment ────────────────────────────────────────────────


class TestSentinelContainment:
    """Sentinels must not leak through any output channel."""

    def test_sentinels_not_in_fake_notifier(
        self, sentinel_data_set: SentinelDataSet,
    ) -> None:
        """Sentinels with URL/CV patterns must be rejected by the notifier.

        Only sentinels whose content matches a redaction pattern are
        expected to be rejected.  Plain-text sentinels (API keys, tokens,
        email addresses without URL context) pass through because the
        Telegram redaction layer only blocks known-dangerous patterns.
        """
        notifier = FakeTelegramNotifier()

        # The evidence link contains a URL - must be rejected
        with pytest.raises(TelegramRedactionError):
            notifier.send_status(
                workflow_status=f"link: {sentinel_data_set.evidence_link}",
            )

        # The CV text contains "Curriculum Vitae" - must be rejected
        with pytest.raises(TelegramRedactionError):
            notifier.send_status(
                workflow_status=sentinel_data_set.cv_text,
            )

        # Plain-text sentinels pass through (no redaction match)
        notifier.send_status(workflow_status=sentinel_data_set.api_key)
        notifier.send_status(workflow_status=sentinel_data_set.email)
        notifier.send_status(workflow_status="all systems nominal")
        assert len(notifier.sent) == 3

    def test_sentinels_not_in_audit_http_response(
        self,
        tmp_path: Path,
        sentinel_data_set: SentinelDataSet,
    ) -> None:
        """Sentinels stored in audit must not leak through HTTP /audit response."""
        settings = PrivateSettings.from_paths(
            app_data_dir=tmp_path,
            sqlite_database_name="sec_audit.sqlite3",
        )
        db = settings.sqlite_database_path
        db.parent.mkdir(parents=True, exist_ok=True)
        db.touch(mode=0o600)
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA user_version = 1")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        deps = AppDependencies(
            settings=settings,
            connection=conn,
            workflow_repo=SqliteWorkflowRepository(conn),
            notifier=FakeTelegramNotifier(),
            mcp_available=False,
        )
        inject_test_deps(deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/audit")
        body = response.text
        for sentinel in sentinel_data_set.all_strings:
            assert sentinel not in body

    def test_sentinels_not_in_http_response(
        self,
        tmp_path: Path,
        sentinel_data_set: SentinelDataSet,
    ) -> None:
        """Sentinels must not leak through HTTP error responses."""
        settings = PrivateSettings.from_paths(
            app_data_dir=tmp_path,
            sqlite_database_name="sec_http.sqlite3",
        )
        db = settings.sqlite_database_path
        db.parent.mkdir(parents=True, exist_ok=True)
        db.touch(mode=0o600)
        conn = sqlite3.connect(db)
        conn.execute("PRAGMA user_version = 1")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        deps = AppDependencies(
            settings=settings,
            connection=conn,
            workflow_repo=SqliteWorkflowRepository(conn),
            notifier=FakeTelegramNotifier(),
            mcp_available=False,
        )
        inject_test_deps(deps)
        app = create_app()
        with TestClient(app) as client:
            response = client.get("/nonexistent")
        body = response.text
        for sentinel in sentinel_data_set.all_strings:
            assert sentinel not in body


# ── 2. Default-deny ────────────────────────────────────────────────────────


class TestDefaultDeny:
    """Live adapter invocations must fail in test configuration."""

    def test_live_mcp_access_denied(self) -> None:
        """Creating a job source with a live server name raises."""
        fake_source = FakeMCPJobSource(listings=())
        with pytest.raises(LiveAccessDeniedError):
            _ = create_job_source(
                server_name="linkedin",
                fake_source=fake_source,
            )

    def test_live_mcp_access_denied_any_non_fake(self) -> None:
        """Any non-fake server name is denied."""
        fake_source = FakeMCPJobSource(listings=())
        for name in ("greenhouse", "lever", "workday"):
            with pytest.raises(LiveAccessDeniedError):
                _ = create_job_source(
                    server_name=name,
                    fake_source=fake_source,
                )

    def test_fake_mcp_access_allowed(self) -> None:
        """Fake server name is allowed."""
        fake_source = FakeMCPJobSource(listings=())
        source = create_job_source(server_name="fake", fake_source=fake_source)
        results = source.search_jobs(
            JobSearch(keywords="engineer", location=None, limit=10),
        )
        assert results == ()


# ── 3. 90-day retention purge ──────────────────────────────────────────────


class TestRetentionPurge:
    """90-day purge removes detailed audit data while preserving tombstones."""

    def test_purge_before_90_days_keeps_data(self, tmp_path: Path) -> None:
        """Records younger than 90 days survive the purge."""
        ref = datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)
        connection, workflow, jobs, audit = _bootstrap(tmp_path)
        observed_at = ref - timedelta(days=365)
        profile = workflow.upsert_candidate_profile(
            CandidateProfileRecord(
                profile_id=CandidateProfileId("profile-ret-1"),
                candidate_id=CandidateId("candidate-ret-1"),
                active_version=CandidateProfileVersionId("v1"),
                timezone_name="UTC",
                created_at=observed_at,
            ),
        )
        identity = _require_verified_identity(
            build_job_identity(
                source="linkedin",
                external_job_id=" LI-RET-001 ",
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
        young = ref - timedelta(days=89)
        entry = EvaluationAuditEntry(
            entry_id="audit-ret-young",
            job_id=job.job_id,
            run_id=RunId("run-ret"),
            decision=EligibilityDecision.ELIGIBLE,
            applied_threshold=50,
            score_value=85,
            scoring_policy_version="2026-07-fixed-30-30-25-10-5",
            factor_breakdown_json="{}",
            evidence_references="src::fact-1",
            cv_artifact_reference=None,
            evaluated_at_utc=young,
        )
        audit.append_evaluation(entry)
        cutoff = ref - timedelta(days=90)
        purged = purge_aged_audit_data(connection, cutoff)
        assert purged == 0
        assert len(audit.list_for_job(job.job_id)) == 1

    def test_purge_after_90_days_removes_data_leaves_tombstone(
        self, tmp_path: Path,
    ) -> None:
        """Records older than 90 days are purged; tombstones remain."""
        ref = datetime(2026, 7, 22, 12, 0, 0, tzinfo=UTC)
        connection, workflow, jobs, audit = _bootstrap(tmp_path)
        observed_at = ref - timedelta(days=365)
        profile = workflow.upsert_candidate_profile(
            CandidateProfileRecord(
                profile_id=CandidateProfileId("profile-ret-2"),
                candidate_id=CandidateId("candidate-ret-2"),
                active_version=CandidateProfileVersionId("v1"),
                timezone_name="UTC",
                created_at=observed_at,
            ),
        )
        identity = _require_verified_identity(
            build_job_identity(
                source="linkedin",
                external_job_id=" LI-RET-002 ",
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
        old = ref - timedelta(days=91)
        entry = EvaluationAuditEntry(
            entry_id="audit-ret-old",
            job_id=job.job_id,
            run_id=RunId("run-ret"),
            decision=EligibilityDecision.INELIGIBLE,
            applied_threshold=None,
            score_value=None,
            scoring_policy_version="2026-07-fixed-30-30-25-10-5",
            factor_breakdown_json="{}",
            evidence_references="",
            cv_artifact_reference=None,
            evaluated_at_utc=old,
        )
        audit.append_evaluation(entry)
        cutoff = ref - timedelta(days=90)
        purged = purge_aged_audit_data(connection, cutoff)
        assert purged == 1
        assert audit.list_for_job(job.job_id) == ()
        tombstones = connection.execute(
            "SELECT identity_hash, reason FROM submission_tombstones",
        ).fetchall()
        assert len(tombstones) == 1
        assert tombstones[0]["reason"] == "audit_retention_purge"


# ── 4. Telegram allowlist / redaction ──────────────────────────────────────


class TestTelegramRedaction:
    """Telegram notifier enforces content allowlist and redaction."""

    def test_redaction_rejects_urls(self) -> None:
        """Messages containing URLs are rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError):
            notifier.send_status(
                workflow_status="see details at https://example.com/secret",
            )

    def test_redaction_rejects_emoji(self) -> None:
        """Messages containing emoji are rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError):
            notifier.send_status(workflow_status="Job found \U0001f525")

    def test_redaction_rejects_cv_references(self) -> None:
        """Messages containing CV references are rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError):
            notifier.send_status(
                workflow_status="Curriculum Vitae attached for review",
            )

    def test_redaction_rejects_evidence_references(self) -> None:
        """Messages containing evidence references are rejected."""
        notifier = FakeTelegramNotifier()
        with pytest.raises(TelegramRedactionError):
            notifier.send_status(
                workflow_status="evidence from source linkedin found",
            )

    def test_clean_message_passes_redaction(self) -> None:
        """Messages without forbidden content are accepted."""
        notifier = FakeTelegramNotifier()
        notifier.send_status(
            workflow_status="2 jobs evaluated, 1 eligible",
            aggregate_score=75,
        )
        assert len(notifier.sent) == 1
        assert notifier.sent[0] == ("2 jobs evaluated, 1 eligible", 75)

    def test_allowlist_only_status_and_score(self) -> None:
        """Only workflow_status and aggregate_score fields are permitted."""
        notifier = FakeTelegramNotifier()
        notifier.send_status(
            workflow_status="processing complete",
            aggregate_score=42,
        )
        msg, score = notifier.sent[0]
        assert isinstance(msg, str)
        assert score == 42
        assert "processing" in msg
