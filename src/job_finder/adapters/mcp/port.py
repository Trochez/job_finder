"""Typed job source port definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from src.job_finder.domain.errors import CandidateValidationError

if TYPE_CHECKING:
    from datetime import datetime


def _require_timezone_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CandidateValidationError(field_name, "must be timezone-aware")


@dataclass(frozen=True, slots=True)
class JobSearch:
    """Search criteria for querying job listings."""

    keywords: str
    location: str | None
    limit: int

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        normalized_keywords = self.keywords.strip()
        if not normalized_keywords:
            msg = "keywords"
            raise CandidateValidationError(msg, "must not be blank")

        if self.limit < 1:
            msg = "limit"
            raise CandidateValidationError(msg, "must be greater than 0")

        normalized_location = None
        if self.location is not None:
            stripped_location = self.location.strip()
            if stripped_location:
                normalized_location = stripped_location

        object.__setattr__(self, "keywords", normalized_keywords)
        object.__setattr__(self, "location", normalized_location)


@dataclass(frozen=True, slots=True)
class JobIdentity:
    """Uniquely identifies a job listing from a source."""

    source: str
    external_job_id: str
    canonical_company_key: str


@dataclass(frozen=True, slots=True)
class JobEvidence:
    """Evidence metadata scraped from a job listing."""

    title: str
    company: str
    location: str
    published_at: datetime
    apply_url: str
    description_excerpt: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        _require_timezone_aware_datetime(self.published_at, "published_at")


@dataclass(frozen=True, slots=True)
class JobListing:
    """Normalized job listing returned by a source adapter."""

    identity: JobIdentity
    evidence: JobEvidence


class JobSourcePort(Protocol):
    """Capability contract for retrieving job listings."""

    def search_jobs(self, search: JobSearch) -> tuple[JobListing, ...]:
        """Return normalized job listings for the given search."""
        ...
