"""Local working-tree CV renderer that simulates Overleaf artifact generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, final, override
from uuid import NAMESPACE_URL, uuid5

from .port import (
    CvRendererPort,
    EvidenceInsufficient,
    RenderedArtifactId,
    RenderRequest,
    RenderResult,
)

if TYPE_CHECKING:
    from pathlib import Path


@final
@dataclass
class LocalOverleafRenderer(CvRendererPort):
    """Renders CV artifacts from a local Overleaf-like working tree.

    This implementation never connects to Overleaf. It checks that the
    working tree contains the requested template sub-directory, then
    writes a minimal placeholder artifact as a ``.tex`` file.
    """

    working_tree_path: Path = field(repr=True)

    @override
    def render(self, request: RenderRequest) -> RenderResult:
        """Render a CV artifact if the template is available locally."""
        working_tree = self.working_tree_path

        if not working_tree.is_dir():
            msg = f"Working tree not found: {working_tree}"
            raise EvidenceInsufficient(detail=msg)

        template_dir = working_tree / request.template_name
        if not template_dir.is_dir():
            msg = (
                f"Template '{request.template_name}' not found "
                f"at {template_dir}"
            )
            raise EvidenceInsufficient(detail=msg)

        # Deterministic artifact ID based on request content
        canonical = (
            f"cv://{request.candidate_profile_id}"
            f"/{request.template_name}"
            f"/{','.join(request.fact_ids)}"
        )
        artifact_id = RenderedArtifactId(uuid5(NAMESPACE_URL, canonical).hex)

        output_file = request.output_path / f"{artifact_id}.tex"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write a minimal placeholder artifact
        latex_content = _build_minimal_latex(template_dir)
        _ = output_file.write_text(latex_content, encoding="utf-8")

        return RenderResult(
            artifact_id=artifact_id,
            output_path=output_file,
            rendered_at=datetime.now(UTC),
            fact_ids_used=request.fact_ids,
        )


def _build_minimal_latex(template_dir: Path) -> str:
    """Generate a minimal LaTeX document from the template directory."""
    cls_files = list(template_dir.glob("*.cls"))
    sty_preamble = ""
    if cls_files:
        cls_name = cls_files[0].stem
        sty_preamble = f"\\documentclass{{{cls_name}}}"
    else:
        sty_preamble = "\\documentclass{article}"

    return (
        f"{sty_preamble}\n"
        "\\begin{document}\n"
        "\\section*{CV}\n"
        "\\end{document}\n"
    )
