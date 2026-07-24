"""Port protocol for CV source acquisition from remote sources like Overleaf."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from job_finder.adapters.cv_renderer.overleaf_config import OverleafConfig


@dataclass(frozen=True, slots=True)
class FetchSourceRequest:
    """Request to fetch CV source from a remote source."""

    overleaf_config: OverleafConfig
    cache_dir: Path
    snapshot_dir: Path


@dataclass(frozen=True, slots=True)
class FetchSourceResult:
    """Outcome of fetching CV source from a remote source."""

    snapshot_dir: Path
    fetched_at: datetime
    revision: str


class CvSourcePort(Protocol):
    """Capability contract for CV source acquisition."""

    def fetch_source(self, request: FetchSourceRequest) -> FetchSourceResult:
        """Fetch CV source files from a remote source."""
        ...
