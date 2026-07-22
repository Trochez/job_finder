"""Job intake normalization — transforms raw MCP listings into canonical records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from job_finder.adapters.repositories.jobs import CanonicalJobUpsert
from job_finder.domain.job_identity import (
    IdentityUnverified,
    build_job_identity,
)

if TYPE_CHECKING:
    from datetime import datetime

    from job_finder.adapters.mcp.port import JobListing
    from job_finder.domain.ids import CandidateProfileId


@dataclass(frozen=True, slots=True)
class NormalizedJobRecord:
    """Flattened, fully-resolved job record combining identity and evidence."""

    job_id: str
    candidate_profile_id: CandidateProfileId
    identity_hash: str
    source: str
    external_job_id: str
    canonical_company_key: str
    title: str
    company: str
    location: str
    published_at: datetime
    apply_url: str
    description_excerpt: str | None


def normalize_job_listing(
    listing: JobListing,
    candidate_profile_id: CandidateProfileId,
) -> CanonicalJobUpsert | IdentityUnverified:
    """Transform a typed MCP ``JobListing`` into a canonical job upsert.

    Builds a job identity from the listing's source, external id, and company
    key.  When the identity can be fully resolved (all three fields present)
    a ``CanonicalJobUpsert`` is returned, ready for persistence.  Otherwise
    an ``IdentityUnverified`` result is returned, which callers can route to
    a separate audit workflow.
    """
    identity_result = build_job_identity(
        source=listing.identity.source,
        external_job_id=listing.identity.external_job_id,
        canonical_company_key=listing.identity.canonical_company_key,
    )

    if isinstance(identity_result, IdentityUnverified):
        return identity_result

    return CanonicalJobUpsert(
        candidate_profile_id=candidate_profile_id,
        identity=identity_result,
        discovered_at=listing.evidence.published_at,
    )
