"""Import candidate profiles with source-backed fact validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

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

if TYPE_CHECKING:
    from datetime import datetime

SUPPORTED_CLAIM_NAMES: Final[tuple[str, ...]] = (
    "certification",
    "domain",
    "education",
    "experience",
    "industry",
    "language",
    "location",
    "role",
    "seniority",
    "skill",
    "summary",
    "tool",
    "work_authorization",
)
_SUPPORTED_CLAIM_NAME_SET: Final[frozenset[str]] = frozenset(SUPPORTED_CLAIM_NAMES)


@dataclass(frozen=True, slots=True)
class CandidateFactImport:
    """A single candidate fact import request."""

    name: str
    value: str
    claim_type: ClaimType
    source_id: CandidateSourceId
    source_kind: SourceKind
    source_locator: str
    source_captured_at: datetime
    source_claim_type: ClaimType
    source_excerpt: str


@dataclass(frozen=True, slots=True)
class CandidateProfileImport:
    """A complete candidate profile import request."""

    candidate_id: CandidateId
    version: CandidateProfileVersionId
    imported_at: datetime
    facts: tuple[CandidateFactImport, ...]


@dataclass(frozen=True, slots=True)
class CandidateFactImportRejection:
    """Details of a rejected fact import."""

    fact_index: int
    fact_name: str
    field_name: str
    detail: str
    action: str


@dataclass(frozen=True, slots=True)
class CandidateProfileImportResult:
    """Result of a candidate profile import operation."""

    profile: CandidateProfile | None
    imported_version: CandidateProfileVersion | None
    accepted_fact_count: int
    rejections: tuple[CandidateFactImportRejection, ...]


def import_candidate_profile(
    *,
    current_profile: CandidateProfile | None,
    profile_import: CandidateProfileImport,
) -> CandidateProfileImportResult:
    """Import a candidate profile, validating and collecting rejections."""
    _validate_profile_identity(
        current_profile=current_profile,
        candidate_id=profile_import.candidate_id,
    )
    _validate_new_version(
        current_profile=current_profile,
        version=profile_import.version,
    )

    rejections = _collect_rejections(profile_import.facts)
    if rejections:
        return CandidateProfileImportResult(
            profile=current_profile,
            imported_version=None,
            accepted_fact_count=0,
            rejections=rejections,
        )

    imported_facts = tuple(
        _build_candidate_fact(
            fact_import=fact_import,
            version=profile_import.version,
            fact_index=fact_index,
        )
        for fact_index, fact_import in enumerate(profile_import.facts, start=1)
    )
    imported_version = CandidateProfileVersion(
        version=profile_import.version,
        sequence_number=_next_sequence_number(current_profile),
        created_at=profile_import.imported_at,
        facts=imported_facts,
        previous_version=_previous_version_id(current_profile),
    )
    imported_profile = _build_profile(
        current_profile=current_profile,
        candidate_id=profile_import.candidate_id,
        imported_version=imported_version,
    )

    return CandidateProfileImportResult(
        profile=imported_profile,
        imported_version=imported_version,
        accepted_fact_count=len(imported_facts),
        rejections=(),
    )


def _validate_profile_identity(
    *,
    current_profile: CandidateProfile | None,
    candidate_id: CandidateId,
) -> None:
    if current_profile is None:
        return

    if current_profile.candidate_id != candidate_id:
        msg = "candidate_id"
        raise CandidateValidationError(
            msg,
            "must match the existing candidate profile",
        )


def _validate_new_version(
    *,
    current_profile: CandidateProfile | None,
    version: CandidateProfileVersionId,
) -> None:
    if current_profile is None:
        return

    if any(
        existing_version.version == version
        for existing_version in current_profile.versions
    ):
        msg = "version"
        raise CandidateValidationError(
            msg,
            "must be a new explicit version identifier",
        )


def _collect_rejections(
    fact_imports: tuple[CandidateFactImport, ...],
) -> tuple[CandidateFactImportRejection, ...]:
    rejections: list[CandidateFactImportRejection] = []

    for fact_index, fact_import in enumerate(fact_imports):
        unsupported_claim_rejection = _unsupported_claim_rejection(
            fact_index=fact_index,
            fact_import=fact_import,
        )
        if unsupported_claim_rejection is not None:
            rejections.append(unsupported_claim_rejection)
            continue

        candidate_validation_error = _candidate_validation_error(fact_import)
        if candidate_validation_error is not None:
            rejections.append(
                CandidateFactImportRejection(
                    fact_index=fact_index,
                    fact_name=fact_import.name,
                    field_name=candidate_validation_error.field_name,
                    detail=str(candidate_validation_error),
                    action=_action_for_field(candidate_validation_error.field_name),
                ),
            )

    return tuple(rejections)


def _unsupported_claim_rejection(
    *,
    fact_index: int,
    fact_import: CandidateFactImport,
) -> CandidateFactImportRejection | None:
    if fact_import.name in _SUPPORTED_CLAIM_NAME_SET:
        return None

    return CandidateFactImportRejection(
        fact_index=fact_index,
        fact_name=fact_import.name,
        field_name="name",
        detail=f"unsupported candidate claim name: {fact_import.name}",
        action=(
            "Use a supported candidate claim name grounded in"
            " source-backed CV evidence."
        ),
    )


def _candidate_validation_error(
    fact_import: CandidateFactImport,
) -> CandidateValidationError | None:
    try:
        _ = _build_candidate_fact(
            fact_import=fact_import,
            version=CandidateProfileVersionId("validation"),
            fact_index=1,
        )
    except CandidateValidationError as error:
        return error

    return None


def _build_candidate_fact(
    *,
    fact_import: CandidateFactImport,
    version: CandidateProfileVersionId,
    fact_index: int,
) -> CandidateFact:
    return CandidateFact(
        fact_id=CandidateFactId(f"{version}:{fact_index}:{fact_import.name}"),
        name=fact_import.name,
        value=fact_import.value,
        claim_type=fact_import.claim_type,
        provenance=FactProvenance(
            source=SourceReference(
                source_id=fact_import.source_id,
                kind=fact_import.source_kind,
                locator=fact_import.source_locator,
                captured_at=fact_import.source_captured_at,
            ),
            source_claim_type=fact_import.source_claim_type,
            derived_claim_type=fact_import.claim_type,
            source_excerpt=fact_import.source_excerpt,
        ),
    )


def _action_for_field(field_name: str) -> str:
    if field_name == "locator":
        return (
            "Add a non-blank source locator that points to the"
            " exact supporting evidence."
        )

    return (
        "Fix the source-backed fact data and resubmit the import"
        " with explicit provenance."
    )


def _next_sequence_number(current_profile: CandidateProfile | None) -> int:
    if current_profile is None:
        return 1

    return current_profile.active.sequence_number + 1


def _previous_version_id(
    current_profile: CandidateProfile | None,
) -> CandidateProfileVersionId | None:
    if current_profile is None:
        return None

    return current_profile.active.version


def _build_profile(
    *,
    current_profile: CandidateProfile | None,
    candidate_id: CandidateId,
    imported_version: CandidateProfileVersion,
) -> CandidateProfile:
    if current_profile is None:
        versions = (imported_version,)
    else:
        versions = (*current_profile.versions, imported_version)

    return CandidateProfile(
        candidate_id=candidate_id,
        versions=versions,
        active_version=imported_version.version,
    )
