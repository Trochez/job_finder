"""Fake Overleaf renderer for deterministic tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from job_finder.adapters.cv_renderer.port import RenderedArtifactId, RenderResult

if TYPE_CHECKING:
    from job_finder.adapters.cv_renderer.cv_source_port import CvSourcePort
    from job_finder.adapters.cv_renderer.port import (
        RenderRequest,
    )


@dataclass
class FakeOverleafRenderer:
    """Fake Overleaf renderer that delegates to a fake source."""

    source: CvSourcePort
    rendered_requests: list[RenderRequest] = field(default_factory=list)

    def render(self, request: RenderRequest) -> RenderResult:
        """Record request and return a deterministic Overleaf artifact."""
        self.rendered_requests.append(request)

        artifact_id = RenderedArtifactId(
            uuid5(NAMESPACE_URL, f"cv://overleaf-fake/{request.template_name}").hex,
        )

        output_file = request.output_path / f"{artifact_id}.tex"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            "\\documentclass{article}\n\\begin{document}\nOverleaf CV\\end{document}\n",
            encoding="utf-8",
        )

        return RenderResult(
            artifact_id=artifact_id,
            output_path=output_file,
            rendered_at=datetime.now(UTC),
            fact_ids_used=request.fact_ids,
        )
