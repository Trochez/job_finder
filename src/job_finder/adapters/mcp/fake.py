"""Fake MCP adapter used for deterministic tests."""

from dataclasses import dataclass
from typing import override

from .port import JobListing, JobSearch, JobSourcePort


@dataclass(frozen=True, slots=True)
class FakeMCPJobSource(JobSourcePort):
    """Deterministic in-memory job source for tests."""

    listings: tuple[JobListing, ...]

    @override
    def search_jobs(self, search: JobSearch) -> tuple[JobListing, ...]:
        """Return matching listings for the provided query."""
        normalized_keywords = search.keywords.casefold()
        normalized_location = (
            search.location.casefold() if search.location is not None else None
        )
        matching_listings = tuple(
            listing
            for listing in self.listings
            if normalized_keywords
            in f"{listing.evidence.title} {listing.evidence.company}".casefold()
            and (
                normalized_location is None
                or normalized_location in listing.evidence.location.casefold()
            )
        )
        return matching_listings[: search.limit]
