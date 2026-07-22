"""LinkedIn MCP client adapter -- structural mock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import final, override

from .policy import FAKE_MCP_SERVER_NAME, LiveAccessDeniedError
from .port import JobListing, JobSearch, JobSourcePort


@dataclass(frozen=True, slots=True)
class LinkedInMcpJobSearch:
    """Structured LinkedIn search query built from a JobSearch."""

    keywords: str
    location: str | None
    limit: int


@final
class LinkedInMcpJobSource(JobSourcePort):
    """Structural mock simulating stickerdaniel/linkedin-mcp-server behavior.

    This adapter does NOT make real network calls. It validates server access
    via the same policy gate used by ``create_job_source()`` and returns empty
    results as a safe default fixture.
    """

    _server_name: str

    def __init__(self, *, server_name: str = "linkedin-mcp") -> None:
        """Initialize with a server name, raising if live access is denied."""
        if server_name != FAKE_MCP_SERVER_NAME:
            raise LiveAccessDeniedError(server_name=server_name)
        self._server_name = server_name

    @override
    def search_jobs(self, search: JobSearch) -> tuple[JobListing, ...]:
        """Simulate an MCP search round-trip without an actual network call.

        The search is parsed into a structured query (``LinkedInMcpJobSearch``)
        and then discarded — this is a structural mock that always returns
        an empty result set.
        """
        _ = self._build_query(search)
        return ()

    def _build_query(self, search: JobSearch) -> LinkedInMcpJobSearch:
        return LinkedInMcpJobSearch(
            keywords=search.keywords,
            location=search.location,
            limit=search.limit,
        )
