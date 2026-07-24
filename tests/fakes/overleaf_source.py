"""Fake Overleaf source for deterministic tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from job_finder.adapters.cv_renderer.cv_source_port import FetchSourceResult

if TYPE_CHECKING:
    from job_finder.adapters.cv_renderer.cv_source_port import (
        FetchSourceRequest,
    )


@dataclass
class FakeOverleafSource:
    """In-memory fake implementing CvSourcePort.

    Records all fetch_source requests and returns canned .tex content.
    """

    fetch_requests: list[FetchSourceRequest] = field(default_factory=list)
    revision: str = "fake_revision_001"

    def fetch_source(self, request: FetchSourceRequest) -> FetchSourceResult:
        """Record request and write canned .tex snapshot."""
        self.fetch_requests.append(request)
        request.snapshot_dir.mkdir(parents=True, exist_ok=True)
        tex_file = request.snapshot_dir / "main.tex"
        tex_file.write_text(
            "\\documentclass{article}\n\\begin{document}\n\\end{document}\n",
            encoding="utf-8",
        )
        return FetchSourceResult(
            snapshot_dir=request.snapshot_dir,
            fetched_at=datetime.now(UTC),
            revision=self.revision,
        )
