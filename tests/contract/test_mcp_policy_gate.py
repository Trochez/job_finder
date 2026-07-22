from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.job_finder.adapters.mcp.fake import FakeMCPJobSource
from src.job_finder.adapters.mcp.policy import LiveAccessDeniedError, create_job_source
from src.job_finder.adapters.mcp.port import (
    JobEvidence,
    JobIdentity,
    JobListing,
    JobSearch,
)


def test_create_job_source_returns_fake_adapter_for_fake_server() -> None:
    listing = JobListing(
        identity=JobIdentity(
            source="fake",
            external_job_id="fake-1",
            canonical_company_key="example-co",
        ),
        evidence=JobEvidence(
            title="Python Engineer",
            company="Example Co",
            location="Remote",
            published_at=datetime(2026, 7, 22, tzinfo=UTC),
            apply_url="https://example.invalid/jobs/fake-1",
            description_excerpt="Build reliable Python services.",
        ),
    )
    fake_source = FakeMCPJobSource(listings=(listing,))

    job_source = create_job_source(server_name="fake", fake_source=fake_source)

    results = job_source.search_jobs(
        JobSearch(keywords="python", location="remote", limit=10)
    )

    assert results == (listing,)
    assert results[0].identity.external_job_id == "fake-1"
    assert results[0].evidence.company == "Example Co"


def test_create_job_source_rejects_live_servers_by_default() -> None:
    fake_source = FakeMCPJobSource(listings=())

    with pytest.raises(LiveAccessDeniedError, match="linkedin"):
        _ = create_job_source(server_name="linkedin", fake_source=fake_source)


def test_job_search_rejects_blank_keywords_and_non_positive_limit() -> None:
    with pytest.raises(Exception, match="keywords"):
        _ = JobSearch(keywords="   ", location="Remote", limit=10)

    with pytest.raises(Exception, match="greater than 0"):
        _ = JobSearch(keywords="python", location="Remote", limit=0)


def test_job_search_normalizes_blank_location_to_none() -> None:
    search = JobSearch(keywords=" python ", location="   ", limit=5)

    assert search.keywords == "python"
    assert search.location is None


def test_job_evidence_rejects_naive_published_at() -> None:
    with pytest.raises(Exception, match="published_at"):
        _ = JobListing(
            identity=JobIdentity(
                source="fake",
                external_job_id="fake-2",
                canonical_company_key="example-co",
            ),
            evidence=JobEvidence(
                title="Backend Engineer",
                company="Example Co",
                location="Remote",
                published_at=datetime(2026, 7, 22),  # noqa: DTZ001 — intentional naive datetime test
                apply_url="https://example.invalid/jobs/fake-2",
            ),
        )
