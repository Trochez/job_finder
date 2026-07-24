"""Typed exception hierarchy for Overleaf integration failures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import override


class OverleafSourceError(Exception):
    """Base class for all Overleaf integration exceptions."""


@dataclass(frozen=True, slots=True)
class OverleafTokenExpired(OverleafSourceError):  # noqa: N818
    """Overleaf API token is expired or invalid."""

    detail: str = "Token expired or invalid"

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class OverleafProjectNotFound(OverleafSourceError):  # noqa: N818
    """Requested Overleaf project does not exist."""

    project_id: str
    detail: str = "Project not found"

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class OverleafRateLimited(OverleafSourceError):  # noqa: N818
    """Overleaf API rate limit exceeded."""

    detail: str = "Rate limited"

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class OverleafUnreachable(OverleafSourceError):  # noqa: N818
    """Overleaf service is unreachable or returning errors."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class GitBinaryMissing(OverleafSourceError):  # noqa: N818
    """Git binary is not available on the system PATH."""

    detail: str = "git binary required for Overleaf operations"

    @override
    def __str__(self) -> str:
        return self.detail
