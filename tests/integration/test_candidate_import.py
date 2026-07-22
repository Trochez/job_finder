from __future__ import annotations

from datetime import UTC, datetime

from job_finder.application.candidate_import import (
    CandidateFactImport,
    CandidateFactImportRejection,
    CandidateProfileImport,
    import_candidate_profile,
)
from job_finder.domain.candidate import (
    CandidateFact,
    CandidateProfile,
    CandidateProfileVersion,
    ClaimType,
    FactProvenance,
    SourceKind,
    SourceReference,
)
from job_finder.domain.ids import (
    CandidateFactId,
    CandidateId,
    CandidateProfileVersionId,
    CandidateSourceId,
)


def test_import_creates_new_profile_version_with_exact_provenance_retention() -> None:
    existing_profile = _existing_profile()

    result = import_candidate_profile(
        current_profile=existing_profile,
        profile_import=CandidateProfileImport(
            candidate_id=CandidateId("candidate-123"),
            version=CandidateProfileVersionId("v2"),
            imported_at=datetime(2026, 7, 23, 9, 30, tzinfo=UTC),
            facts=(
                CandidateFactImport(
                    name="skill",
                    value="Python",
                    claim_type=ClaimType.NORMALIZED,
                    source_id=CandidateSourceId("cv-2026-08"),
                    source_kind=SourceKind.CV,
                    source_locator="experience[0].skills[1]",
                    source_captured_at=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
                    source_claim_type=ClaimType.VERBATIM,
                    source_excerpt="Built internal automation in Python.",
                ),
            ),
        ),
    )

    assert result.rejections == ()
    assert result.accepted_fact_count == 1
    assert result.imported_version is not None
    assert result.profile is not None
    imported_profile = result.profile
    assert imported_profile.active.version == CandidateProfileVersionId("v2")
    assert imported_profile.active.previous_version == CandidateProfileVersionId("v1")
    assert imported_profile.active.sequence_number == 2

    imported_fact = imported_profile.active.facts[0]
    assert imported_fact.fact_id == CandidateFactId("v2:1:skill")
    assert imported_fact.provenance.source.source_id == CandidateSourceId("cv-2026-08")
    assert imported_fact.provenance.source.locator == "experience[0].skills[1]"
    assert imported_fact.provenance.source.captured_at == datetime(
        2026,
        7,
        22,
        12,
        0,
        tzinfo=UTC,
    )
    assert (
        imported_fact.provenance.source_excerpt
        == "Built internal automation in Python."
    )


def test_import_rejects_unsupported_claims_without_creating_a_new_version() -> None:
    existing_profile = _existing_profile()

    result = import_candidate_profile(
        current_profile=existing_profile,
        profile_import=CandidateProfileImport(
            candidate_id=CandidateId("candidate-123"),
            version=CandidateProfileVersionId("v2"),
            imported_at=datetime(2026, 7, 23, 9, 30, tzinfo=UTC),
            facts=(
                CandidateFactImport(
                    name="inferred_skill",
                    value="Distributed systems expert",
                    claim_type=ClaimType.NORMALIZED,
                    source_id=CandidateSourceId("cv-2026-08"),
                    source_kind=SourceKind.CV,
                    source_locator="summary",
                    source_captured_at=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
                    source_claim_type=ClaimType.NORMALIZED,
                    source_excerpt="Worked with backend systems.",
                ),
                CandidateFactImport(
                    name="skill",
                    value="Python",
                    claim_type=ClaimType.NORMALIZED,
                    source_id=CandidateSourceId("cv-2026-08"),
                    source_kind=SourceKind.CV,
                    source_locator="   ",
                    source_captured_at=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
                    source_claim_type=ClaimType.VERBATIM,
                    source_excerpt="Built internal automation in Python.",
                ),
            ),
        ),
    )

    assert result.profile == existing_profile
    assert result.imported_version is None
    assert result.accepted_fact_count == 0
    assert result.rejections == (
        CandidateFactImportRejection(
            fact_index=0,
            fact_name="inferred_skill",
            field_name="name",
            detail="unsupported candidate claim name: inferred_skill",
            action=(
                "Use a supported candidate claim name "
                "grounded in source-backed CV evidence."
            ),
        ),
        CandidateFactImportRejection(
            fact_index=1,
            fact_name="skill",
            field_name="locator",
            detail="locator: must not be blank",
            action=(
                "Add a non-blank source locator that "
                "points to the exact supporting evidence."
            ),
        ),
    )
    retained_profile = result.profile
    assert retained_profile is not None
    assert retained_profile.active.version == CandidateProfileVersionId("v1")
    assert len(retained_profile.versions) == 1


def _existing_profile() -> CandidateProfile:
    initial_fact = CandidateFact(
        fact_id=CandidateFactId("fact-summary-v1"),
        name="summary",
        value="Backend engineer",
        claim_type=ClaimType.VERBATIM,
        provenance=FactProvenance(
            source=SourceReference(
                source_id=CandidateSourceId("cv-2026-07"),
                kind=SourceKind.CV,
                locator="summary",
                captured_at=datetime(2026, 7, 22, 8, 0, tzinfo=UTC),
            ),
            source_claim_type=ClaimType.VERBATIM,
            derived_claim_type=ClaimType.VERBATIM,
            source_excerpt="Backend engineer",
        ),
    )
    initial_version = CandidateProfileVersion(
        version=CandidateProfileVersionId("v1"),
        sequence_number=1,
        created_at=datetime(2026, 7, 22, 8, 30, tzinfo=UTC),
        facts=(initial_fact,),
    )
    return CandidateProfile(
        candidate_id=CandidateId("candidate-123"),
        versions=(initial_version,),
        active_version=CandidateProfileVersionId("v1"),
    )
