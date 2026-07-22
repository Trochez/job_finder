"""Policy gate for MCP-backed job sources."""

from dataclasses import dataclass
from typing import Final, override

from .port import JobSourcePort

FAKE_MCP_SERVER_NAME: Final = "fake"


@dataclass(frozen=True, slots=True)
class LiveAccessDeniedError(Exception):
    """Raised when code attempts to use a live MCP target."""

    server_name: str

    @override
    def __str__(self) -> str:
        return f"live MCP access is denied for server '{self.server_name}'"


def create_job_source(*, server_name: str, fake_source: JobSourcePort) -> JobSourcePort:
    """Return the permitted job source for the requested MCP server."""
    match server_name:
        case "fake":
            return fake_source
        case denied_server_name:
            raise LiveAccessDeniedError(server_name=denied_server_name)
