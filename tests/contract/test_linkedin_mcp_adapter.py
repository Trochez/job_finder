"""Contract tests for the LinkedInMcpJobSource adapter."""

from __future__ import annotations

import pytest
from src.job_finder.adapters.mcp.linkedin_client import LinkedInMcpJobSource
from src.job_finder.adapters.mcp.policy import (
    FAKE_MCP_SERVER_NAME,
    LiveAccessDeniedError,
)
from src.job_finder.adapters.mcp.port import JobSearch


class TestLinkedInMcpJobSourceConstruction:
    """Server-name validation at construction time."""

    def test_accepts_fake_server_name(self) -> None:
        source = LinkedInMcpJobSource(server_name=FAKE_MCP_SERVER_NAME)
        assert source is not None

    def test_rejects_live_server_name(self) -> None:
        with pytest.raises(LiveAccessDeniedError, match="linkedin"):
            _ = LinkedInMcpJobSource(server_name="linkedin-mcp")

    def test_rejects_unknown_server_name(self) -> None:
        with pytest.raises(LiveAccessDeniedError, match="some-other"):
            _ = LinkedInMcpJobSource(server_name="some-other-server")


class TestLinkedInMcpJobSourceSearch:
    """Empty-result behavior and input validation."""

    def test_returns_empty_tuple_for_unmatched_keywords(self) -> None:
        source = LinkedInMcpJobSource(server_name=FAKE_MCP_SERVER_NAME)
        results = source.search_jobs(
            JobSearch(
                keywords="quantum blockchain engineer",
                location="Remote",
                limit=10,
            )
        )
        assert results == ()

    def test_returns_empty_tuple_for_unusual_location(self) -> None:
        source = LinkedInMcpJobSource(server_name=FAKE_MCP_SERVER_NAME)
        results = source.search_jobs(
            JobSearch(keywords="engineer", location="antarctica", limit=5)
        )
        assert results == ()

    def test_returns_empty_tuple_when_limit_is_exceeded(self) -> None:
        source = LinkedInMcpJobSource(server_name=FAKE_MCP_SERVER_NAME)
        results = source.search_jobs(
            JobSearch(keywords="python developer", location="Berlin", limit=100)
        )
        assert results == ()

    def test_rejects_blank_keywords(self) -> None:
        source = LinkedInMcpJobSource(server_name=FAKE_MCP_SERVER_NAME)
        with pytest.raises(Exception, match="keywords"):
            _ = source.search_jobs(
                JobSearch(keywords="   ", location="Remote", limit=10)
            )

    def test_rejects_non_positive_limit(self) -> None:
        source = LinkedInMcpJobSource(server_name=FAKE_MCP_SERVER_NAME)
        with pytest.raises(Exception, match="greater than 0"):
            _ = source.search_jobs(
                JobSearch(keywords="python", location="Remote", limit=0)
            )
