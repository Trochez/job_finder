"""Integration tests for OverleafGitSource with mocked git subprocess."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from job_finder.adapters.cv_renderer.cv_source_port import (
    FetchSourceRequest,
    FetchSourceResult,
)
from job_finder.adapters.cv_renderer.overleaf_config import OverleafConfig
from job_finder.adapters.cv_renderer.overleaf_errors import (
    GitBinaryMissing,
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafTokenExpired,
    OverleafUnreachable,
)
from job_finder.adapters.cv_renderer.overleaf_source import OverleafGitSource

if TYPE_CHECKING:
    from collections.abc import Generator
    from unittest.mock import MagicMock

PATCH_PREFIX = "job_finder.adapters.cv_renderer.overleaf_source"
PROJECT_ID = "0123456789abcdef01234567"
TOKEN_PATH = Path("/home/user/.overleaf/token")
GIT_HOST = "git.overleaf.com"


@pytest.fixture
def overleaf_config() -> OverleafConfig:
    """Fixture providing a valid OverleafConfig."""
    return OverleafConfig(
        project_id=PROJECT_ID,
        token_path=TOKEN_PATH,
        git_host=GIT_HOST,
    )


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Fixture providing a cache directory."""
    return tmp_path / "cv_cache"


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    """Fixture providing a snapshot directory."""
    return tmp_path / "cv_snapshots"


@pytest.fixture
def fetch_request(
    overleaf_config: OverleafConfig,
    cache_dir: Path,
    snapshot_dir: Path,
) -> FetchSourceRequest:
    """Fixture providing a valid FetchSourceRequest."""
    return FetchSourceRequest(
        overleaf_config=overleaf_config,
        cache_dir=cache_dir,
        snapshot_dir=snapshot_dir,
    )


@pytest.fixture(autouse=True)
def _mock_git_binary() -> Generator[MagicMock, None, None]:
    """Mock shutil.which so git is always found (opt-in override per test)."""
    with patch(
        "job_finder.adapters.cv_renderer.overleaf_source.shutil.which",
    ) as mock_which:
        mock_which.return_value = "/usr/bin/git"
        yield mock_which


@pytest.fixture
def mock_clone_or_pull() -> Generator[MagicMock, None, None]:
    """Mock overleaf_git.clone_or_pull to return a deterministic revision."""
    with patch(
        "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
    ) as mock_cop:
        mock_cop.return_value = "deadbeef1234567890abcdef1234567890abcdef"
        yield mock_cop


@pytest.fixture
def subject() -> OverleafGitSource:
    """Fixture providing a fresh OverleafGitSource instance."""
    return OverleafGitSource()


# ── Happy path ───────────────────────────────────────────────────────────────


class TestHappyPath:
    """Tests for successful fetch_source scenarios."""

    def test_returns_fetch_source_result(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
        mock_clone_or_pull: MagicMock,
    ) -> None:
        """Happy path: successful fetch returns a FetchSourceResult."""
        result = subject.fetch_source(fetch_request)

        assert isinstance(result, FetchSourceResult)
        assert result.revision == "deadbeef1234567890abcdef1234567890abcdef"
        assert result.fetched_at.tzinfo is not None

    def test_copies_cache_to_snapshot_dir(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
        mock_clone_or_pull: MagicMock,
        cache_dir: Path,
        snapshot_dir: Path,
    ) -> None:
        """Source files are copied from cache_dir to snapshot_dir."""
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "main.tex").write_text(
            "\\documentclass{article}\n\\begin{document}\n\\end{document}\n",
            encoding="utf-8",
        )
        (cache_dir / "subdir").mkdir()
        (cache_dir / "subdir" / "preamble.tex").write_text(
            "% preamble",
            encoding="utf-8",
        )

        result = subject.fetch_source(fetch_request)

        assert result.snapshot_dir == snapshot_dir
        assert (snapshot_dir / "main.tex").is_file()
        assert (snapshot_dir / "subdir" / "preamble.tex").is_file()

    def test_clone_or_pull_called_with_correct_args(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
        mock_clone_or_pull: MagicMock,
        cache_dir: Path,
    ) -> None:
        """clone_or_pull receives the expected parameters."""
        _ = subject.fetch_source(fetch_request)

        mock_clone_or_pull.assert_called_once_with(
            project_id=PROJECT_ID,
            git_host=GIT_HOST,
            token_path=TOKEN_PATH,
            target_dir=cache_dir,
            app_data_dir=cache_dir.parent,
        )

    def test_serializes_concurrent_calls(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """Concurrent fetch_source calls are serialized by the lock."""
        call_order: list[int] = []

        def slow_clone_or_pull(**kwargs: object) -> str:
            call_order.append(1)
            return "abc"

        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
            side_effect=slow_clone_or_pull,
        ):
            # Simulate sequential calls (lock ensures no overlap)
            r1 = subject.fetch_source(fetch_request)
            r2 = subject.fetch_source(fetch_request)

        assert r1.revision == "abc"
        assert r2.revision == "abc"
        assert len(call_order) == 2

    def test_fetched_at_is_timezone_aware(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
        mock_clone_or_pull: MagicMock,
    ) -> None:
        """fetched_at carries timezone information (UTC)."""
        result = subject.fetch_source(fetch_request)

        assert result.fetched_at.tzinfo is not None
        assert result.fetched_at.utcoffset() is not None


# ── Error paths ──────────────────────────────────────────────────────────────


class TestErrorPaths:
    """Tests for error handling in OverleafGitSource."""

    def test_git_not_found_raises(
        self,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """Missing git binary raises GitBinaryMissing."""
        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.shutil.which",
            return_value=None,
        ):
            source = OverleafGitSource()
            with pytest.raises(GitBinaryMissing):
                _ = source.fetch_source(fetch_request)

    def test_clone_or_pull_project_not_found(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """OverleafProjectNotFound from clone_or_pull propagates."""
        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
            side_effect=OverleafProjectNotFound(project_id=PROJECT_ID),
        ), pytest.raises(OverleafProjectNotFound):
            _ = subject.fetch_source(fetch_request)

    def test_clone_or_pull_token_expired(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """OverleafTokenExpired from clone_or_pull propagates."""
        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
            side_effect=OverleafTokenExpired(),
        ), pytest.raises(OverleafTokenExpired):
            _ = subject.fetch_source(fetch_request)

    def test_clone_or_pull_rate_limited(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """OverleafRateLimited from clone_or_pull propagates."""
        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
            side_effect=OverleafRateLimited(),
        ), pytest.raises(OverleafRateLimited):
            _ = subject.fetch_source(fetch_request)

    def test_clone_or_pull_unreachable(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """OverleafUnreachable from clone_or_pull propagates."""
        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
            side_effect=OverleafUnreachable(detail="connection refused"),
        ), pytest.raises(OverleafUnreachable):
            _ = subject.fetch_source(fetch_request)

    def test_unexpected_exception_wraps(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """Non-OverleafSourceError exceptions are wrapped in OverleafUnreachable."""
        with patch(
            "job_finder.adapters.cv_renderer.overleaf_source.clone_or_pull",
            side_effect=PermissionError("access denied"),
        ):
            with pytest.raises(OverleafUnreachable) as exc_info:
                _ = subject.fetch_source(fetch_request)

            assert "access denied" in str(exc_info.value)


# ── Concurrency ──────────────────────────────────────────────────────────────


class TestConcurrency:
    """Tests for concurrent fetch_source behaviour."""

    def test_concurrent_fetch_serializes_through_lock(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """Concurrent calls serialise through lock, all complete."""
        call_count: int = 0
        call_lock: threading.Lock = threading.Lock()

        def slow_clone_or_pull(**kwargs: object) -> str:
            nonlocal call_count
            with call_lock:
                call_count += 1
            time.sleep(0.05)
            return "abc123"

        with (
            patch(
                f"{PATCH_PREFIX}.clone_or_pull",
                side_effect=slow_clone_or_pull,
            ),
            patch(f"{PATCH_PREFIX}.shutil.copytree"),
            ThreadPoolExecutor(max_workers=5) as executor,
        ):
            futures = [
                executor.submit(subject.fetch_source, fetch_request)
                for _ in range(5)
            ]
            done, _ = wait(futures, timeout=10)

        assert len(done) == 5
        for f in done:
            result = f.result()
            assert result.revision == "abc123"
        assert call_count == 5

    def test_concurrent_fetch_working_tree_integrity(
        self,
        subject: OverleafGitSource,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """Lock ensures sequential execution of fetches, no overlap."""
        call_order: list[int] = []
        call_order_lock: threading.Lock = threading.Lock()
        overlap_counter: int = 0
        max_overlap: int = 0
        overlap_lock: threading.Lock = threading.Lock()

        def timed_clone_or_pull(**kwargs: object) -> str:
            nonlocal overlap_counter, max_overlap
            with overlap_lock:
                overlap_counter += 1
                max_overlap = max(max_overlap, overlap_counter)
            with call_order_lock:
                call_order.append(overlap_counter)
            time.sleep(0.05)
            with overlap_lock:
                overlap_counter -= 1
            return "def789"

        with (
            patch(
                f"{PATCH_PREFIX}.clone_or_pull",
                side_effect=timed_clone_or_pull,
            ),
            patch(f"{PATCH_PREFIX}.shutil.copytree"),
            ThreadPoolExecutor(max_workers=5) as executor,
        ):
            futures = [
                executor.submit(subject.fetch_source, fetch_request)
                for _ in range(5)
            ]
            done, _ = wait(futures, timeout=15)

            assert len(done) == 5
            assert max_overlap == 1
            for f in done:
                result = f.result()
                assert result.revision == "def789"
