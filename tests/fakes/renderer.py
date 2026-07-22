"""Fake CV renderer for deterministic tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import override
from uuid import NAMESPACE_URL, uuid5

from job_finder.adapters.cv_renderer.port import (
    CvRendererPort,
    RenderedArtifactId,
    RenderRequest,
    RenderResult,
)


@dataclass
class FakeRenderer(CvRendererPort):
    """In-memory fake renderer implementing the CvRendererPort protocol.

    Records all render requests and also exposes the legacy
    ``render_markdown`` helper for backward compatibility.
    """

    rendered_requests: list[RenderRequest] = field(default_factory=list)

    @override
    def render(self, request: RenderRequest) -> RenderResult:
        """Record the request and return a deterministic result."""
        self.rendered_requests.append(request)

        artifact_id = RenderedArtifactId(
            uuid5(NAMESPACE_URL, f"cv://fake/{request.template_name}").hex,
        )

        output_file = request.output_path / f"{artifact_id}.tex"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        _ = output_file.write_text(
            "\\documentclass{article}\n\\begin{document}\n\\end{document}\n",
            encoding="utf-8",
        )

        return RenderResult(
            artifact_id=artifact_id,
            output_path=output_file,
            rendered_at=datetime.now(UTC),
            fact_ids_used=request.fact_ids,
        )

    # ── legacy helpers (kept for existing test backward compatibility) ──────────

    rendered_markdown: list[str] = field(default_factory=list)

    def render_markdown(self, markdown: str) -> str:
        """Legacy method: render a markdown string to a minimal HTML fragment."""
        self.rendered_markdown.append(markdown)
        if markdown.startswith("# "):
            return f"<h1>{markdown.removeprefix('# ')}</h1>"
        return markdown
