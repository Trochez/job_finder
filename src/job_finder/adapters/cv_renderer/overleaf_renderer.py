"""Overleaf Git renderer implementing CvRendererPort via remote source."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, final, override
from uuid import NAMESPACE_URL, uuid5

from .cv_source_port import FetchSourceRequest
from .port import (
    CvRendererPort,
    EvidenceInsufficient,
    RenderedArtifactId,
    RenderRequest,
    RenderResult,
)

if TYPE_CHECKING:
    from .cv_source_port import CvSourcePort
    from .overleaf_config import OverleafConfig


@final
@dataclass
class OverleafGitRenderer(CvRendererPort):
    """Renders CV artifacts from Overleaf-sourced working tree.

    Delegates source acquisition to a ``CvSourcePort`` implementation,
    then reads ``.tex`` files from the fetched snapshot directory.
    """

    source: CvSourcePort
    overleaf_config: OverleafConfig
    cache_dir: Path = field(repr=True)

    @override
    def render(self, request: RenderRequest) -> RenderResult:
        """Render a CV artifact from Overleaf source."""
        snapshot_dir = Path(tempfile.mkdtemp(prefix="overleaf_snapshot_"))
        try:
            fetch_request = FetchSourceRequest(
                overleaf_config=self.overleaf_config,
                cache_dir=self.cache_dir,
                snapshot_dir=snapshot_dir,
            )
            fetch_result = self.source.fetch_source(fetch_request)

            primary_tex = self._locate_primary_tex(
                fetch_result.snapshot_dir,
                request.template_name,
            )

            # Deterministic artifact ID (matched LocalOverleafRenderer)
            canonical = (
                f"cv://{request.candidate_profile_id}"
                f"/{request.template_name}"
                f"/{','.join(request.fact_ids)}"
            )
            artifact_id = RenderedArtifactId(uuid5(NAMESPACE_URL, canonical).hex)

            output_file = request.output_path / f"{artifact_id}.tex"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            latex_content = primary_tex.read_text(encoding="utf-8")
            _ = output_file.write_text(latex_content, encoding="utf-8")

            return RenderResult(
                artifact_id=artifact_id,
                output_path=output_file,
                rendered_at=datetime.now(UTC),
                fact_ids_used=request.fact_ids,
            )
        finally:
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir, ignore_errors=True)

    @staticmethod
    def _locate_primary_tex(snapshot_dir: Path, template_name: str) -> Path:
        """Locate the primary ``.tex`` file in a snapshot directory.

        Resolution order:
        1. ``snapshot_dir / template_name / ``*.tex`` (template sub-directory)
        2. Root-level ``snapshot_dir / ``*.tex`` files

        Raises ``EvidenceInsufficient`` when no ``.tex`` file is found.
        """
        # Check template sub-directory first
        template_dir = snapshot_dir / template_name
        if template_dir.is_dir():
            tex_files = sorted(template_dir.glob("*.tex"))
            if tex_files:
                return tex_files[0]

        # Fall back to root-level .tex files
        root_tex = sorted(snapshot_dir.glob("*.tex"))
        if root_tex:
            return root_tex[0]

        msg = f"No .tex files found in snapshot at {snapshot_dir}"
        raise EvidenceInsufficient(detail=msg)


__all__ = [
    "OverleafGitRenderer",
]
