from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from src.job_finder.domain.candidate import (
    CandidateFact,
    CandidateProfile,
    CandidateProfileVersion,
    ClaimType,
    FactProvenance,
    SourceKind,
    SourceReference,
)
from src.job_finder.domain.errors import CandidateValidationError
from src.job_finder.domain.ids import (
    CandidateFactId,
    CandidateId,
    CandidateProfileVersionId,
    CandidateSourceId,
)


def test_candidate_fact_keeps_provenance_without_strengthening() -> None:
    source = SourceReference(
        source_id=CandidateSourceId("cv-2026-07"),
        kind=SourceKind.CV,
        locator="experience[0]",
        captured_at=datetime(2026, 7, 22, tzinfo=UTC),
    )

    fact = CandidateFact(
        fact_id=CandidateFactId("fact-python"),
        name="skill",
        value="Python",
        claim_type=ClaimType.NORMALIZED,
        provenance=FactProvenance(
            source=source,
            source_claim_type=ClaimType.VERBATIM,
            derived_claim_type=ClaimType.NORMALIZED,
            source_excerpt="Built internal automation in Python.",
        ),
    )

    assert fact.provenance.source.kind is SourceKind.CV
    assert fact.provenance.derived_claim_type is ClaimType.NORMALIZED
    assert fact.claim_type is ClaimType.NORMALIZED


def test_candidate_fact_rejects_claim_strengthening() -> None:
    source = SourceReference(
        source_id=CandidateSourceId("record-1"),
        kind=SourceKind.CANDIDATE_RECORD,
        locator="skills.python",
        captured_at=datetime(2026, 7, 22, tzinfo=UTC),
    )

    with pytest.raises(
        CandidateValidationError,
        match="stronger than source claim type",
    ):
        _ = CandidateFact(
            fact_id=CandidateFactId("fact-stronger"),
            name="skill",
            value="Python expert",
            claim_type=ClaimType.VERBATIM,
            provenance=FactProvenance(
                source=source,
                source_claim_type=ClaimType.NORMALIZED,
                derived_claim_type=ClaimType.VERBATIM,
                source_excerpt="Python",
            ),
        )


def test_candidate_profile_is_versioned_and_immutable() -> None:
    source = SourceReference(
        source_id=CandidateSourceId("cv-2026-07"),
        kind=SourceKind.CV,
        locator="summary",
        captured_at=datetime(2026, 7, 22, tzinfo=UTC),
    )
    summary_fact = CandidateFact(
        fact_id=CandidateFactId("fact-summary"),
        name="summary",
        value="Backend engineer",
        claim_type=ClaimType.VERBATIM,
        provenance=FactProvenance(
            source=source,
            source_claim_type=ClaimType.VERBATIM,
            derived_claim_type=ClaimType.VERBATIM,
            source_excerpt="Backend engineer",
        ),
    )
    version_1 = CandidateProfileVersion(
        version=CandidateProfileVersionId("v1"),
        sequence_number=1,
        created_at=datetime(2026, 7, 22, 7, tzinfo=UTC),
        facts=(summary_fact,),
    )
    version_2 = CandidateProfileVersion(
        version=CandidateProfileVersionId("v2"),
        sequence_number=2,
        created_at=datetime(2026, 7, 22, 8, tzinfo=UTC),
        facts=(summary_fact,),
        previous_version=CandidateProfileVersionId("v1"),
    )

    profile = CandidateProfile(
        candidate_id=CandidateId("candidate-123"),
        versions=(version_1, version_2),
        active_version=CandidateProfileVersionId("v2"),
    )

    assert profile.active.version == CandidateProfileVersionId("v2")
    assert profile.active.previous_version == CandidateProfileVersionId("v1")
    assert profile.active.sequence_number == 2

    with pytest.raises(FrozenInstanceError):
        profile.active_version = "v3"  # pyright: ignore[reportAttributeAccessIssue]


def test_candidate_reference_and_version_require_timezone_aware_datetimes() -> None:
    with pytest.raises(CandidateValidationError, match="captured_at"):
        _ = SourceReference(
            source_id=CandidateSourceId("cv-2026-07"),
            kind=SourceKind.CV,
            locator="summary",
            captured_at=datetime(2026, 7, 22),  # noqa: DTZ001 — intentional naive datetime test
        )

    source = SourceReference(
        source_id=CandidateSourceId("cv-2026-07"),
        kind=SourceKind.CV,
        locator="summary",
        captured_at=datetime(2026, 7, 22, tzinfo=UTC),
    )
    fact = CandidateFact(
        fact_id=CandidateFactId("fact-summary"),
        name="summary",
        value="Backend engineer",
        claim_type=ClaimType.VERBATIM,
        provenance=FactProvenance(
            source=source,
            source_claim_type=ClaimType.VERBATIM,
            derived_claim_type=ClaimType.VERBATIM,
            source_excerpt="Backend engineer",
        ),
    )

    with pytest.raises(CandidateValidationError, match="created_at"):
        _ = CandidateProfileVersion(
            version=CandidateProfileVersionId("v1"),
            sequence_number=1,
            created_at=datetime(2026, 7, 22, 7),  # noqa: DTZ001 — intentional naive datetime test
            facts=(fact,),
        )
