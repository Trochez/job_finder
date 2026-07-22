"""Candidate domain models for job_finder."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from .errors import CandidateValidationError

if TYPE_CHECKING:
    from datetime import datetime

    from .ids import (
        CandidateFactId,
        CandidateId,
        CandidateProfileVersionId,
        CandidateSourceId,
    )


class SourceKind(StrEnum):
    """Kind of source from which candidate data originates."""

    CV = "cv"
    CANDIDATE_RECORD = "candidate_record"


class ClaimType(StrEnum):
    """Strength category of a factual claim extracted from a source."""

    SUMMARY = "summary"
    NORMALIZED = "normalized"
    VERBATIM = "verbatim"


_CLAIM_TYPE_STRENGTH = {
    ClaimType.SUMMARY: 1,
    ClaimType.NORMALIZED: 2,
    ClaimType.VERBATIM: 3,
}


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise CandidateValidationError(field_name, "must not be blank")


def _require_timezone_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CandidateValidationError(field_name, "must be timezone-aware")


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Reference to a specific source of candidate information."""

    source_id: CandidateSourceId
    kind: SourceKind
    locator: str
    captured_at: datetime

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.source_id, "source_id")
        _require_text(self.locator, "locator")
        _require_timezone_aware_datetime(self.captured_at, "captured_at")


@dataclass(frozen=True, slots=True)
class FactProvenance:
    """Provenance metadata describing how a fact was derived from a source."""

    source: SourceReference
    source_claim_type: ClaimType
    derived_claim_type: ClaimType
    source_excerpt: str

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.source_excerpt, "source_excerpt")

        if (
            _CLAIM_TYPE_STRENGTH[self.derived_claim_type]
            > _CLAIM_TYPE_STRENGTH[self.source_claim_type]
        ):
            msg = "derived_claim_type"
            raise CandidateValidationError(
                msg,
                "cannot be stronger than source claim type",
            )


@dataclass(frozen=True, slots=True)
class CandidateFact:
    """A single fact extracted about a candidate."""

    fact_id: CandidateFactId
    name: str
    value: str
    claim_type: ClaimType
    provenance: FactProvenance

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.fact_id, "fact_id")
        _require_text(self.name, "name")
        _require_text(self.value, "value")

        if self.claim_type is not self.provenance.derived_claim_type:
            msg = "claim_type"
            raise CandidateValidationError(
                msg,
                "must match provenance derived claim type",
            )


@dataclass(frozen=True, slots=True)
class CandidateProfileVersion:
    """A versioned snapshot of candidate facts at a point in time."""

    version: CandidateProfileVersionId
    sequence_number: int
    created_at: datetime
    facts: tuple[CandidateFact, ...]
    previous_version: CandidateProfileVersionId | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.version, "version")
        _require_timezone_aware_datetime(self.created_at, "created_at")

        if self.sequence_number < 1:
            msg = "sequence_number"
            raise CandidateValidationError(msg, "must be a positive integer")

        fact_ids = {fact.fact_id for fact in self.facts}
        if len(fact_ids) != len(self.facts):
            msg = "facts"
            raise CandidateValidationError(
                msg,
                "must have unique fact_id values within a version",
            )

        if self.previous_version is not None:
            _require_text(self.previous_version, "previous_version")


@dataclass(frozen=True, slots=True)
class CandidateProfile:
    """A candidate profile composed of versioned snapshots."""

    candidate_id: CandidateId
    versions: tuple[CandidateProfileVersion, ...]
    active_version: CandidateProfileVersionId

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.active_version, "active_version")

        if not self.versions:
            msg = "versions"
            raise CandidateValidationError(msg, "must not be empty")

        versions_by_id = {version.version: version for version in self.versions}
        if len(versions_by_id) != len(self.versions):
            msg = "versions"
            raise CandidateValidationError(
                msg,
                "must have unique version identifiers",
            )

        if self.active_version not in versions_by_id:
            msg = "active_version"
            raise CandidateValidationError(
                msg,
                "must reference an existing version",
            )

        previous_version: CandidateProfileVersionId | None = None
        previous_created_at = None
        expected_sequence_number = 1

        for version in self.versions:
            if version.sequence_number != expected_sequence_number:
                msg = "versions"
                raise CandidateValidationError(
                    msg,
                    "must have contiguous sequence numbers starting at 1",
                )

            if (
                previous_created_at is not None
                and version.created_at < previous_created_at
            ):
                msg = "versions"
                raise CandidateValidationError(
                    msg,
                    "must be ordered by created_at",
                )

            if version.previous_version != previous_version:
                msg = "versions"
                raise CandidateValidationError(
                    msg,
                    "must form a single forward version chain",
                )

            previous_version = version.version
            previous_created_at = version.created_at
            expected_sequence_number += 1

        if self.versions[-1].version != self.active_version:
            msg = "active_version"
            raise CandidateValidationError(
                msg,
                "must be the newest version",
            )

    @property
    def active(self) -> CandidateProfileVersion:
        """Return the currently active profile version."""
        for version in self.versions:
            if version.version == self.active_version:
                return version

        msg = "active_version"
        raise CandidateValidationError(
            msg,
            "is missing from candidate profile",
        )
