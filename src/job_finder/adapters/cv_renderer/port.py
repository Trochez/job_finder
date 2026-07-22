"""Typed CV renderer port definitions for Overleaf artifact generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, NewType, Protocol, override

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from job_finder.domain.ids import CandidateProfileId

RenderedArtifactId = NewType("RenderedArtifactId", str)


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """Parameters for rendering a CV artifact."""

    candidate_profile_id: CandidateProfileId
    template_name: str
    output_path: Path
    fact_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Outcome of a CV render operation."""

    artifact_id: RenderedArtifactId
    output_path: Path
    rendered_at: datetime
    fact_ids_used: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceInsufficient(Exception):  # noqa: N818
    """Raised when the working tree lacks a required template."""

    detail: str

    @override
    def __str__(self) -> str:
        return self.detail


class CvRendererPort(Protocol):
    """Capability contract for rendering CV artifacts."""

    def render(self, request: RenderRequest) -> RenderResult:
        """Render a CV artifact for the given request."""
        ...
