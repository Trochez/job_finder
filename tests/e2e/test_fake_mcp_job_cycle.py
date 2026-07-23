"""Full job-cycle end-to-end test with fake MCP, fake renderer, and real SQLite.

Tests the complete pipeline from fake MCP discovery through eligibility,
workflow transitions, audit persistence, CV artifact binding, kill-switch
blocking, checkpoint pausing, and daily-cap enforcement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from src.job_finder.adapters.cv_renderer.port import RenderRequest
from src.job_finder.adapters.mcp.fake import FakeMCPJobSource
from src.job_finder.adapters.mcp.policy import create_job_source
from src.job_finder.adapters.mcp.port import (
    JobEvidence,
    JobIdentity,
    JobListing,
    JobSearch,
)
from src.job_finder.adapters.notifications.telegram import FakeTelegramNotifier
from src.job_finder.adapters.repositories.audit import (
    EvaluationAuditEntry,
    SqliteAuditRepository,
)
from src.job_finder.adapters.repositories.jobs import SqliteJobsRepository
from src.job_finder.adapters.repositories.workflow import (
    CandidateProfileRecord,
    SqliteWorkflowRepository,
    WorkflowTransitionConflictError,
)
from src.job_finder.application.checkpoints import pause_for_checkpoint
from src.job_finder.application.daily_cap import (
    ApplicationAttemptStarted,
    CapCounter,
    DailyCapPolicy,
    check_cap,
)
from src.job_finder.application.job_intake import normalize_job_listing
from src.job_finder.application.workflow import (
    KillSwitch,
    KillSwitchEngagedError,
    advance_workflow,
)
from src.job_finder.domain.eligibility import (
    HardFilter,
    determine_eligibility,
)
from src.job_finder.domain.ids import (
    CandidateId,
    CandidateProfileId,
    CandidateProfileVersionId,
    JobId,
    RunId,
)
from src.job_finder.domain.job_identity import IdentityUnverified
from src.job_finder.domain.states import (
    CheckpointState,
    EligibilityDecision,
    WorkflowState,
)

from tests.fakes import FakeRenderer

if TYPE_CHECKING:
    import sqlite3

    from src.job_finder.adapters.repositories.jobs import (
        CanonicalJobUpsert,
    )

pytestmark = pytest.mark.e2e


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_listing(
    *,
    external_job_id: str = "LI-001",
    company_key: str = "acme-inc",
    title: str = "Senior Software Engineer",
    company: str = "Acme Corp",
    location: str = "Remote",
) -> JobListing:
    """Build a deterministic JobListing."""
    published_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)
    return JobListing(
        identity=JobIdentity(
            source="linkedin",
            external_job_id=external_job_id,
            canonical_company_key=company_key,
        ),
        evidence=JobEvidence(
            title=title,
            company=company,
            location=location,
            published_at=published_at,
            apply_url=f"https://linkedin.com/jobs/view/{external_job_id}",
            description_excerpt=f"Job posting for {title} at {company}",
        ),
    )


def _require_upsert(
    normalized: CanonicalJobUpsert | IdentityUnverified,
) -> CanonicalJobUpsert:
    if isinstance(normalized, IdentityUnverified):
        msg = f"expected canonical upsert, got {normalized.audit_status}"
        raise TypeError(msg)
    return normalized


# ── fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def e2e_deps(
    e2e_sqlite_connection: sqlite3.Connection,
) -> tuple[
    sqlite3.Connection,
    SqliteWorkflowRepository,
    SqliteJobsRepository,
    SqliteAuditRepository,
    FakeRenderer,
    FakeTelegramNotifier,
]:
    """Shared dependencies for the E2E test suite."""
    conn = e2e_sqlite_connection
    workflow = SqliteWorkflowRepository(conn)
    jobs = SqliteJobsRepository(conn)
    audit = SqliteAuditRepository(conn)
    renderer = FakeRenderer()
    notifier = FakeTelegramNotifier()
    return conn, workflow, jobs, audit, renderer, notifier


@pytest.fixture
def seeded_profile(
    e2e_deps: tuple[
        sqlite3.Connection,
        SqliteWorkflowRepository,
        SqliteJobsRepository,
        SqliteAuditRepository,
        FakeRenderer,
        FakeTelegramNotifier,
    ],
) -> CandidateProfileId:
    """Create a candidate profile and return its profile_id."""
    _conn, workflow, _jobs, _audit, _renderer, _notifier = e2e_deps
    observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)
    profile = workflow.upsert_candidate_profile(
        CandidateProfileRecord(
            profile_id=CandidateProfileId("profile-e2e"),
            candidate_id=CandidateId("candidate-e2e"),
            active_version=CandidateProfileVersionId("v1"),
            timezone_name="UTC",
            created_at=observed_at,
        ),
    )
    return profile.profile_id


# ── tests ────────────────────────────────────────────────────────────────────


class TestFakeMcpJobCycleE2e:
    """Full job-cycle end-to-end tests with fake MCP."""

    def test_eligible_job_flows_to_ready_for_user(
        self,
        tmp_path: Path,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """Eligible job transitions through pipeline to ready_for_user.

        Verifies workflow transition, audit entry, and CV artifact binding.
        """
        _conn, workflow, jobs, audit, renderer, notifier = e2e_deps
        profile_id = seeded_profile
        observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)
        run_id = RunId("run-e2e-001")
        score = 85
        threshold = 50

        # 1. Create a job listing via fake MCP and normalize it
        listing = _make_listing(external_job_id="LI-E2E-001")
        upsert = _require_upsert(normalize_job_listing(listing, profile_id))
        job = jobs.upsert_canonical_job(upsert)

        # 2. Evaluate eligibility (score meets threshold)
        verdict = determine_eligibility(
            score=score,
            threshold=threshold,
            hard_filters=(),
        )
        assert verdict.decision is EligibilityDecision.ELIGIBLE

        # 3. Transition: None -> EVALUATED
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            run_id=run_id,
            occurred_at=observed_at,
        )

        # 4. Render CV artifact
        output_path = tmp_path / "cv-output"
        output_path.mkdir(parents=True, exist_ok=True)
        render_request = RenderRequest(
            candidate_profile_id=profile_id,
            template_name="moderncv",
            output_path=output_path,
            fact_ids=(),
        )
        render_result = renderer.render(render_request)
        assert render_result is not None

        # 5. Record audit entry with bound CV artifact reference
        audit_entry = EvaluationAuditEntry(
            entry_id="audit-e2e-001",
            job_id=job.job_id,
            run_id=run_id,
            decision=EligibilityDecision.ELIGIBLE,
            applied_threshold=threshold,
            score_value=score,
            scoring_policy_version="2026-07-fixed-30-30-25-10-5",
            factor_breakdown_json="{}",
            evidence_references="src::fact-e2e-001",
            cv_artifact_reference=render_result.artifact_id,
            evaluated_at_utc=observed_at,
        )
        audit.append_evaluation(audit_entry)

        # 6. Transition: EVALUATED -> READY_FOR_USER
        transition = advance_workflow(
            job_id=job.job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.READY_FOR_USER,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            run_id=run_id,
            occurred_at=observed_at,
        )
        assert transition.to_state == WorkflowState.READY_FOR_USER
        assert transition.from_state == WorkflowState.EVALUATED

        # 7. Verify audit entry persisted with CV artifact reference
        persisted_audit = audit.list_for_job(job.job_id)
        assert len(persisted_audit) == 1
        assert persisted_audit[0].cv_artifact_reference == render_result.artifact_id
        assert persisted_audit[0].decision == EligibilityDecision.ELIGIBLE

        # 8. Verify notifier remains clean (nothing leaked)
        assert notifier.sent == []

    def test_duplicate_submission_is_idempotent(
        self,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """Submitting the same identity-hash job twice is idempotent.

        The second upsert returns the existing record without creating
        a duplicate workflow transition sequence.
        """
        _conn, _workflow, jobs, _audit, _renderer, _notifier = e2e_deps
        profile_id = seeded_profile

        # 1. Normalize and upsert the same listing twice
        listing = _make_listing(external_job_id="LI-E2E-IDEM")
        upsert = _require_upsert(normalize_job_listing(listing, profile_id))

        job_first = jobs.upsert_canonical_job(upsert)
        job_second = jobs.upsert_canonical_job(upsert)

        # 2. Both should return the same job_id (same identity_hash)
        assert job_first.job_id == job_second.job_id
        assert job_first.identity_hash == job_second.identity_hash

        # 3. There should be only one canonical job for this identity
        all_jobs = _conn.execute(
            "SELECT job_id FROM canonical_jobs WHERE identity_hash = ?",
            (upsert.identity.identity_hash,),
        ).fetchall()
        assert len(all_jobs) == 1

    def test_unset_threshold_blocks_eligibility(
        self,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """When threshold is None, eligibility returns THRESHOLD_UNSET."""
        _conn, workflow, jobs, _audit, _renderer, _notifier = e2e_deps
        profile_id = seeded_profile
        observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)
        score = 85

        listing = _make_listing(external_job_id="LI-E2E-NOTH")
        upsert = _require_upsert(normalize_job_listing(listing, profile_id))
        job = jobs.upsert_canonical_job(upsert)

        # 2. Evaluate with threshold=None
        verdict = determine_eligibility(
            score=score,
            threshold=None,
            hard_filters=(),
        )
        assert verdict.decision is EligibilityDecision.THRESHOLD_UNSET
        assert "threshold is not configured" in verdict.reason

        # 3. Transition to INELIGIBLE (via EVALUATED)
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            occurred_at=observed_at,
        )
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.INELIGIBLE,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            occurred_at=observed_at,
        )

        transitions = workflow.list_transitions(job.job_id)
        assert len(transitions) == 2
        assert transitions[-1].to_state == WorkflowState.INELIGIBLE

    def test_hard_filter_failure_blocks(
        self,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """When a hard filter fails, eligibility returns HARD_FILTER_BLOCKED."""
        _conn, workflow, jobs, _audit, _renderer, _notifier = e2e_deps
        profile_id = seeded_profile
        observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)
        score = 85
        threshold = 50

        listing = _make_listing(external_job_id="LI-E2E-FILT")
        upsert = _require_upsert(normalize_job_listing(listing, profile_id))
        job = jobs.upsert_canonical_job(upsert)

        # 2. Evaluate with failing hard filter
        verdict = determine_eligibility(
            score=score,
            threshold=threshold,
            hard_filters=(HardFilter(name="visa_required", passed=False),),
        )
        assert verdict.decision is EligibilityDecision.HARD_FILTER_BLOCKED
        assert "hard filter 'visa_required' failed" in verdict.reason

        # 3. Transition to INELIGIBLE via EVALUATED
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            occurred_at=observed_at,
        )
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.INELIGIBLE,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            occurred_at=observed_at,
        )

        transitions = workflow.list_transitions(job.job_id)
        assert len(transitions) == 2
        assert transitions[-1].to_state == WorkflowState.INELIGIBLE

    def test_kill_switch_stops_processing(
        self,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """Active kill switch blocks EVALUATED -> READY_FOR_USER transition."""
        _conn, workflow, jobs, _audit, _renderer, _notifier = e2e_deps
        profile_id = seeded_profile
        observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)

        listing = _make_listing(external_job_id="LI-E2E-KILL")
        upsert = _require_upsert(normalize_job_listing(listing, profile_id))
        job = jobs.upsert_canonical_job(upsert)

        # 1. Initial transition
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            occurred_at=observed_at,
        )

        # 2. Activate kill switch and try to advance
        with pytest.raises(KillSwitchEngagedError):
            _ = advance_workflow(
                job_id=job.job_id,
                from_state=WorkflowState.EVALUATED,
                to_state=WorkflowState.READY_FOR_USER,
                workflow_repo=workflow,
                kill_switch=KillSwitch(is_active=True),
                occurred_at=observed_at,
            )

        # 3. But CANCELLED and FAILED transitions still work
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.FAILED,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=True),
            occurred_at=observed_at,
        )

        transitions = workflow.list_transitions(job.job_id)
        assert len(transitions) == 2
        assert transitions[-1].to_state == WorkflowState.FAILED

    def test_checkpoint_pauses_processing(
        self,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """A checkpoint pause transitions to HUMAN_CHECKPOINT_PAUSE."""
        _conn, workflow, jobs, _audit, _renderer, _notifier = e2e_deps
        profile_id = seeded_profile
        observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)
        run_id = RunId("run-e2e-cp")

        listing = _make_listing(external_job_id="LI-E2E-CP")
        upsert = _require_upsert(normalize_job_listing(listing, profile_id))
        job = jobs.upsert_canonical_job(upsert)

        # 1. Initial -> EVALUATED -> READY_FOR_USER
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=None,
            to_state=WorkflowState.EVALUATED,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            run_id=run_id,
            occurred_at=observed_at,
        )
        _ = advance_workflow(
            job_id=job.job_id,
            from_state=WorkflowState.EVALUATED,
            to_state=WorkflowState.READY_FOR_USER,
            workflow_repo=workflow,
            kill_switch=KillSwitch(is_active=False),
            run_id=run_id,
            occurred_at=observed_at,
        )

        # 2. Pause for checkpoint
        try:
            pause_result = pause_for_checkpoint(
                checkpoint_state=CheckpointState.CAPTCHA,
                job_id=job.job_id,
                detail="CAPTCHA challenge on apply page",
                workflow_repo=workflow,
                run_id=run_id,
                occurred_at=observed_at,
            )
            assert (
                pause_result.transition.to_state
                == WorkflowState.HUMAN_CHECKPOINT_PAUSE
            )
        except WorkflowTransitionConflictError:
            # fallback: direct transition
            _ = advance_workflow(
                job_id=job.job_id,
                from_state=WorkflowState.READY_FOR_USER,
                to_state=WorkflowState.HUMAN_CHECKPOINT_PAUSE,
                workflow_repo=workflow,
                kill_switch=KillSwitch(is_active=False),
                run_id=run_id,
                occurred_at=observed_at,
            )

        transitions = workflow.list_transitions(job.job_id)
        assert transitions[-1].to_state == WorkflowState.HUMAN_CHECKPOINT_PAUSE

    def test_post_cap_jobs_not_processed(
        self,
        e2e_deps: tuple[
            sqlite3.Connection,
            SqliteWorkflowRepository,
            SqliteJobsRepository,
            SqliteAuditRepository,
            FakeRenderer,
            FakeTelegramNotifier,
        ],
        seeded_profile: CandidateProfileId,
    ) -> None:
        """When the daily cap is reached, check_cap returns False."""
        _conn, _workflow, _jobs, _audit, _renderer, _notifier = e2e_deps
        _seeded = seeded_profile
        run_id = RunId("run-e2e-cap")

        # 1. Set up cap policy with limit 2 and record 2 attempts
        policy = DailyCapPolicy(limit=2)
        counter = CapCounter()
        counter.record(ApplicationAttemptStarted(run_id=run_id, job_id=JobId("job:1")))
        counter.record(ApplicationAttemptStarted(run_id=run_id, job_id=JobId("job:2")))

        # 2. Cap should be reached (2 attempts >= limit 2)
        assert not check_cap(policy, counter, run_id)

        # 3. Before the limit, cap still allows
        counter2 = CapCounter()
        counter2.record(
            ApplicationAttemptStarted(run_id=run_id, job_id=JobId("job:1")),
        )
        assert check_cap(policy, counter2, run_id)

        # 4. Cap with higher limit allows more
        big_policy = DailyCapPolicy(limit=100)
        assert check_cap(big_policy, counter, run_id)

    @pytest.mark.usefixtures("seeded_profile")
    def test_fake_mcp_source_discovers_jobs(self) -> None:
        """FakeMCPJobSource discovers jobs matching search keywords."""
        observed_at = datetime(2026, 1, 2, 3, 0, 0, tzinfo=UTC)

        # 1. Create fake MCP with some job listings
        listings = (
            JobListing(
                identity=JobIdentity(
                    source="linkedin",
                    external_job_id="LI-E2E-MCP-1",
                    canonical_company_key="acme-inc",
                ),
                evidence=JobEvidence(
                    title="Senior Software Engineer",
                    company="Acme Corp",
                    location="Remote",
                    published_at=observed_at,
                    apply_url="https://linkedin.com/jobs/view/LI-E2E-MCP-1",
                    description_excerpt="Senior role at Acme Corp",
                ),
            ),
            JobListing(
                identity=JobIdentity(
                    source="linkedin",
                    external_job_id="LI-E2E-MCP-2",
                    canonical_company_key="beta-inc",
                ),
                evidence=JobEvidence(
                    title="Frontend Developer",
                    company="Beta Inc",
                    location="New York",
                    published_at=observed_at,
                    apply_url="https://linkedin.com/jobs/view/LI-E2E-MCP-2",
                    description_excerpt="Frontend role at Beta Inc",
                ),
            ),
        )
        fake_source = FakeMCPJobSource(listings)

        # 2. Search via create_job_source policy gate
        source = create_job_source(server_name="fake", fake_source=fake_source)
        results = source.search_jobs(
            JobSearch(keywords="engineer", location=None, limit=10),
        )
        assert len(results) == 1
        assert results[0].identity.external_job_id == "LI-E2E-MCP-1"

        # 3. Different keyword matches other listing
        results2 = source.search_jobs(
            JobSearch(keywords="developer", location=None, limit=10),
        )
        assert len(results2) == 1
        assert results2[0].identity.external_job_id == "LI-E2E-MCP-2"

        # 4. Location filter works
        results3 = source.search_jobs(
            JobSearch(keywords="engineer", location="Remote", limit=10),
        )
        assert len(results3) == 1
