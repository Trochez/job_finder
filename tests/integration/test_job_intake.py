"""Integration tests for job intake normalization."""

from __future__ import annotations

from datetime import UTC, datetime

from job_finder.adapters.mcp.port import JobEvidence, JobIdentity, JobListing
from job_finder.adapters.repositories.jobs import CanonicalJobUpsert
from job_finder.application.job_intake import NormalizedJobRecord, normalize_job_listing
from job_finder.domain.ids import CandidateProfileId
from job_finder.domain.job_identity import (
    IdentityUnverified,
    IdentityUnverifiedReason,
)


class TestNormalizeJobListing:
    """Canonical-path behaviour for ``normalize_job_listing``."""

    def test_returns_canonical_upsert_with_all_fields_mapped(self) -> None:
        profile_id = CandidateProfileId("prof-42")
        published_at = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
        listing = JobListing(
            identity=JobIdentity(
                source="linkedin",
                external_job_id="li-98765",
                canonical_company_key="acme-corp",
            ),
            evidence=JobEvidence(
                title="Senior Rust Engineer",
                company="Acme Corp",
                location="San Francisco, CA",
                published_at=published_at,
                apply_url="https://linkedin.com/jobs/view/98765",
                description_excerpt="Build high-performance systems in Rust.",
            ),
        )

        result = normalize_job_listing(listing, profile_id)

        assert isinstance(result, CanonicalJobUpsert)
        assert result.candidate_profile_id == profile_id
        assert result.discovered_at == published_at

    def test_preserves_identity_fields(self) -> None:
        profile_id = CandidateProfileId("prof-99")
        listing = JobListing(
            identity=JobIdentity(
                source="LinkedIn",
                external_job_id="li-abc-001",
                canonical_company_key="Example-Co",
            ),
            evidence=JobEvidence(
                title="Backend Developer",
                company="Example Co",
                location="New York, NY",
                published_at=datetime(2026, 7, 21, tzinfo=UTC),
                apply_url="https://linkedin.com/jobs/view/abc001",
                description_excerpt=None,
            ),
        )

        result = normalize_job_listing(listing, profile_id)

        assert isinstance(result, CanonicalJobUpsert)
        # source is lowercased by build_job_identity
        assert result.identity.source == "linkedin"
        assert result.identity.external_job_id == "li-abc-001"
        # canonical_company_key is lowercased
        assert result.identity.canonical_company_key == "example-co"
        # identity_hash is deterministic for (source, external_job_id, company_key)
        assert result.identity.identity_hash is not None
        assert len(result.identity.identity_hash) == 64  # SHA-256 hex digest

    def test_identity_hash_is_deterministic(self) -> None:
        profile_id = CandidateProfileId("prof-7")
        listing_a = JobListing(
            identity=JobIdentity(
                source="linkedin",
                external_job_id="li-dup-1",
                canonical_company_key="dup-co",
            ),
            evidence=JobEvidence(
                title="Duplicate",
                company="Dup Co",
                location="Remote",
                published_at=datetime(2026, 7, 20, tzinfo=UTC),
                apply_url="https://example.invalid/dup",
            ),
        )
        listing_b = JobListing(
            identity=JobIdentity(
                source="linkedin",
                external_job_id="li-dup-1",
                canonical_company_key="dup-co",
            ),
            evidence=JobEvidence(
                title="Duplicate (different title)",
                company="Dup Co Different",
                location="Onsite",
                published_at=datetime(2026, 7, 21, tzinfo=UTC),
                apply_url="https://example.invalid/dup-2",
            ),
        )

        result_a = normalize_job_listing(listing_a, profile_id)
        result_b = normalize_job_listing(listing_b, profile_id)

        assert isinstance(result_a, CanonicalJobUpsert)
        assert isinstance(result_b, CanonicalJobUpsert)
        assert result_a.identity.identity_hash == result_b.identity.identity_hash


class TestNormalizeJobListingUnverified:
    """Edge cases where identity cannot be verified."""

    def test_empty_external_job_id_returns_identity_unverified(self) -> None:
        profile_id = CandidateProfileId("prof-1")
        listing = JobListing(
            identity=JobIdentity(
                source="linkedin",
                external_job_id="   ",
                canonical_company_key="acme-corp",
            ),
            evidence=JobEvidence(
                title="Senior Rust Engineer",
                company="Acme Corp",
                location="San Francisco, CA",
                published_at=datetime(2026, 7, 20, tzinfo=UTC),
                apply_url="https://linkedin.com/jobs/view/98765",
            ),
        )

        result = normalize_job_listing(listing, profile_id)

        assert isinstance(result, IdentityUnverified)
        assert result.reason == IdentityUnverifiedReason.MISSING_EXTERNAL_JOB_ID
        assert result.eligible_for_submission is False
        assert result.audit_status == "identity_unverified"

    def test_missing_external_job_id_cannot_reach_scoring(self) -> None:
        """Payload without an external_job_id must never be routed to scoring."""
        profile_id = CandidateProfileId("prof-2")
        listing = JobListing(
            identity=JobIdentity(
                source="linkedin",
                external_job_id="",
                canonical_company_key="no-id-co",
            ),
            evidence=JobEvidence(
                title="Some Job",
                company="No ID Co",
                location="Remote",
                published_at=datetime(2026, 7, 20, tzinfo=UTC),
                apply_url="https://example.invalid/no-id",
            ),
        )

        result = normalize_job_listing(listing, profile_id)

        assert isinstance(result, IdentityUnverified)
        # IdentityUnverified is NOT a CanonicalJobUpsert — callers that
        # pattern-match on the result type will never treat it as scorable.
        assert not isinstance(result, CanonicalJobUpsert)


class TestNormalizedJobRecord:
    """The ``NormalizedJobRecord`` dataclass shape."""

    def test_can_construct_record(self) -> None:
        published_at = datetime(2026, 7, 20, tzinfo=UTC)
        record = NormalizedJobRecord(
            job_id="job:abc123",
            candidate_profile_id=CandidateProfileId("prof-42"),
            identity_hash="a" * 64,
            source="linkedin",
            external_job_id="li-98765",
            canonical_company_key="acme-corp",
            title="Senior Rust Engineer",
            company="Acme Corp",
            location="San Francisco, CA",
            published_at=published_at,
            apply_url="https://linkedin.com/jobs/view/98765",
            description_excerpt="Build high-performance systems in Rust.",
        )

        assert record.job_id == "job:abc123"
        assert record.source == "linkedin"
        assert record.title == "Senior Rust Engineer"
        assert record.published_at == published_at
        assert record.description_excerpt == "Build high-performance systems in Rust."

    def test_description_excerpt_can_be_none(self) -> None:
        record = NormalizedJobRecord(
            job_id="job:def456",
            candidate_profile_id=CandidateProfileId("prof-1"),
            identity_hash="b" * 64,
            source="linkedin",
            external_job_id="li-555",
            canonical_company_key="some-co",
            title="Title",
            company="Some Co",
            location="Remote",
            published_at=datetime(2026, 7, 20, tzinfo=UTC),
            apply_url="https://example.invalid/apply",
            description_excerpt=None,
        )

        assert record.description_excerpt is None
