"""Overleaf Git source implementing CvSourcePort for remote CV acquisition."""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import final

from .cv_source_port import FetchSourceRequest, FetchSourceResult
from .overleaf_errors import GitBinaryMissing, OverleafSourceError, OverleafUnreachable
from .overleaf_git import clone_or_pull


@final
@dataclass
class OverleafGitSource:
    """Fetches CV source from Overleaf via Git subprocess.

    Uses ``threading.Lock`` to serialise concurrent ``fetch_source``
    calls, preventing working-tree corruption. Must be used as a
    singleton in ``AppDependencies`` for the lock to be effective.
    """

    _fetch_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def fetch_source(self, request: FetchSourceRequest) -> FetchSourceResult:
        """Fetch CV source files from Overleaf.

        Checks ``git`` binary availability, acquires a per-instance
        lock, then delegates to ``overleaf_git.clone_or_pull``.
        Fetched files are copied to ``request.snapshot_dir`` inside
        the lock for TOCTOU safety.
        """
        if shutil.which("git") is None:
            raise GitBinaryMissing

        with self._fetch_lock:
            return self._fetch_sync(request)

    def _fetch_sync(self, request: FetchSourceRequest) -> FetchSourceResult:
        """Synchronous fetch executed inside the per-instance lock."""
        config = request.overleaf_config
        cache_dir = request.cache_dir
        snapshot_dir = request.snapshot_dir

        try:
            revision = clone_or_pull(
                project_id=config.project_id,
                git_host=config.git_host,
                token_path=config.token_path,
                target_dir=cache_dir,
                app_data_dir=cache_dir.parent,
            )
        except OverleafSourceError:
            raise
        except Exception as exc:
            raise OverleafUnreachable(detail=str(exc)) from exc

        # Copy to snapshot_dir inside lock (TOCTOU-safe for cache_dir)
        if cache_dir.exists():
            _ = shutil.copytree(cache_dir, snapshot_dir, dirs_exist_ok=True)

        return FetchSourceResult(
            snapshot_dir=snapshot_dir,
            fetched_at=datetime.now(UTC),
            revision=revision,
        )


__all__ = [
    "OverleafGitSource",
]
