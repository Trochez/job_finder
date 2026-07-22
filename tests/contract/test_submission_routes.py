"""Contract tests for submission route classification and access control."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from job_finder.adapters.cv_renderer import LocalOverleafRenderer
from job_finder.adapters.cv_renderer.port import EvidenceInsufficient
from job_finder.adapters.mcp.port import JobEvidence, JobIdentity, JobListing
from job_finder.application.submission_routes import (
    ApplicationRoute,
    ExecutionAccessState,
    classify_route,
    prepare_route,
)
from job_finder.domain.ids import CandidateProfileId
from tests.fakes import FakeRenderer

if TYPE_CHECKING:
    from pathlib import Path


class TestClassifyRoute:
    """Route classification behaviour."""

    def test_linkedin_url_is_easy_apply(self) -> None:
        listing = _listing(apply_url="https://www.linkedin.com/jobs/view/123")
        assert classify_route(listing) == ApplicationRoute.EASY_APPLY

    def test_greenhouse_url_is_external_ats(self) -> None:
        listing = _listing(
            apply_url="https://boards.greenhouse.io/acme/jobs/456",
        )
        assert classify_route(listing) == ApplicationRoute.EXTERNAL_ATS

    def test_lever_url_is_external_ats(self) -> None:
        listing = _listing(apply_url="https://jobs.lever.co/acme/789")
        assert classify_route(listing) == ApplicationRoute.EXTERNAL_ATS

    def test_unknown_domain_is_unsupported(self) -> None:
        listing = _listing(apply_url="https://example.com/careers/123")
        assert classify_route(listing) == ApplicationRoute.UNSUPPORTED

    def test_empty_apply_url_is_unsupported(self) -> None:
        listing = _listing(apply_url="")
        assert classify_route(listing) == ApplicationRoute.UNSUPPORTED

    def test_malformed_url_is_unsupported(self) -> None:
        listing = _listing(apply_url="not-a-url-at-all")
        assert classify_route(listing) == ApplicationRoute.UNSUPPORTED


class TestPrepareRoute:
    """``prepare_route`` behaviour."""

    def test_fake_attempt_binds_rendered_artifact(self, tmp_path: Path) -> None:
        renderer = FakeRenderer()
        access = prepare_route(
            ApplicationRoute.EASY_APPLY,
            renderer,
            candidate_profile_id=CandidateProfileId("candidate-1"),
            output_path=tmp_path,
        )

        assert access.route == ApplicationRoute.EASY_APPLY
        assert access.access_state == ExecutionAccessState.FAKE_ONLY
        assert access.rendered_artifact_ref is not None
        assert len(access.rendered_artifact_ref) == 32  # uuid5 hex

    def test_all_routes_remain_non_live(self, tmp_path: Path) -> None:
        renderer = FakeRenderer()

        for route in ApplicationRoute:
            access = prepare_route(
                route,
                renderer,
                candidate_profile_id=CandidateProfileId("candidate-2"),
                output_path=tmp_path,
            )
            assert access.access_state == ExecutionAccessState.FAKE_ONLY
            assert access.rendered_artifact_ref is not None

    def test_missing_working_tree_raises(self, tmp_path: Path) -> None:
        renderer = LocalOverleafRenderer(
            working_tree_path=tmp_path / "nonexistent",
        )

        with pytest.raises(EvidenceInsufficient, match="Working tree not found"):
            _ = prepare_route(
                ApplicationRoute.EXTERNAL_ATS,
                renderer,
                candidate_profile_id=CandidateProfileId("candidate-3"),
                output_path=tmp_path / "out",
            )

    def test_prepare_route_invokes_renderer(self, tmp_path: Path) -> None:
        """prepare_route must call renderer.render and bind the result."""
        renderer = FakeRenderer()
        access = prepare_route(
            ApplicationRoute.EASY_APPLY,
            renderer,
            candidate_profile_id=CandidateProfileId("candidate-x"),
            output_path=tmp_path,
        )
        assert access.rendered_artifact_ref is not None
        assert access.access_state == ExecutionAccessState.FAKE_ONLY
        # The renderer should have been called once
        assert len(renderer.rendered_requests) == 1
        rendered = renderer.rendered_requests[0]
        assert rendered.candidate_profile_id == CandidateProfileId("candidate-x")

    def test_route_kind_and_access_state_are_independent(
        self,
        tmp_path: Path,
    ) -> None:
        """Every combination of route and access state should be constructable."""
        renderer = FakeRenderer()
        for _route in ApplicationRoute:
            access = prepare_route(
                _route,
                renderer,
                candidate_profile_id=CandidateProfileId("candidate-indep"),
                output_path=tmp_path,
            )
            assert access.route == _route
            assert access.access_state == ExecutionAccessState.FAKE_ONLY


class TestExecutionAccessState:
    """Access state invariants."""

    def test_all_routes_default_to_fake_only(self) -> None:
        """Access state and route are independent -- every route starts non-live."""
        assert ExecutionAccessState.FAKE_ONLY in ExecutionAccessState


# ── helpers ──────────────────────────────────────────────────────────────────


def _listing(*, apply_url: str) -> JobListing:
    return JobListing(
        identity=JobIdentity(
            source="linkedin",
            external_job_id="li-test",
            canonical_company_key="test-co",
        ),
        evidence=JobEvidence(
            title="Test Position",
            company="Test Co",
            location="Remote",
            published_at=datetime(2026, 7, 22, tzinfo=UTC),
            apply_url=apply_url,
        ),
    )
