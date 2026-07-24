"""Tests for CvSourcePort protocol and associated dataclasses."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import pytest

from job_finder.adapters.cv_renderer.cv_source_port import (
    CvSourcePort,
    FetchSourceRequest,
    FetchSourceResult,
)
from job_finder.adapters.cv_renderer.overleaf_config import OverleafConfig

PROJECT_ID = "0123456789abcdef01234567"
TOKEN_PATH = Path("/home/user/.overleaf/token")


@pytest.fixture
def overleaf_config() -> OverleafConfig:
    """Fixture providing a valid OverleafConfig."""
    return OverleafConfig(project_id=PROJECT_ID, token_path=TOKEN_PATH)


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


class TestFetchSourceRequest:
    """Tests for FetchSourceRequest frozen dataclass."""

    def test_creates_dataclass(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        snapshot_dir: Path,
    ) -> None:
        """Happy path: all fields produce a valid FetchSourceRequest."""
        request = FetchSourceRequest(
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
            snapshot_dir=snapshot_dir,
        )

        assert request.overleaf_config == overleaf_config
        assert request.cache_dir == cache_dir
        assert request.snapshot_dir == snapshot_dir

    def test_is_frozen(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        snapshot_dir: Path,
    ) -> None:
        """FetchSourceRequest is frozen and cannot be mutated."""
        request = FetchSourceRequest(
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
            snapshot_dir=snapshot_dir,
        )

        with pytest.raises(AttributeError):
            request.cache_dir = Path("/other/path")  # pyright: ignore[reportAttributeAccessIssue]


class TestFetchSourceResult:
    """Tests for FetchSourceResult frozen dataclass."""

    def test_creates_dataclass(self, snapshot_dir: Path) -> None:
        """Happy path: all fields produce a valid FetchSourceResult."""
        now = datetime.now(UTC)
        result = FetchSourceResult(
            snapshot_dir=snapshot_dir,
            fetched_at=now,
            revision="abc123",
        )

        assert result.snapshot_dir == snapshot_dir
        assert result.fetched_at == now
        assert result.revision == "abc123"

    def test_is_frozen(self, snapshot_dir: Path) -> None:
        """FetchSourceResult is frozen and cannot be mutated."""
        now = datetime.now(UTC)
        result = FetchSourceResult(
            snapshot_dir=snapshot_dir,
            fetched_at=now,
            revision="abc123",
        )

        with pytest.raises(AttributeError):
            result.revision = "def456"  # pyright: ignore[reportAttributeAccessIssue]


class TestCvSourcePort:
    """Tests for CvSourcePort protocol."""

    def test_is_protocol(self) -> None:
        """CvSourcePort is a Protocol class."""
        assert issubclass(CvSourcePort, Protocol)

    def test_has_fetch_source_method(self) -> None:
        """CvSourcePort declares fetch_source method."""
        assert hasattr(CvSourcePort, "fetch_source")
        assert callable(CvSourcePort.fetch_source)

    def test_concrete_implementation_satisfies_contract(
        self,
        fetch_request: FetchSourceRequest,
    ) -> None:
        """A class implementing fetch_source satisfies CvSourcePort."""

        class OverleafCvSource:
            """Concrete implementation of CvSourcePort."""

            def fetch_source(
                self,
                request: FetchSourceRequest,
            ) -> FetchSourceResult:
                return FetchSourceResult(
                    snapshot_dir=request.snapshot_dir,
                    fetched_at=datetime.now(UTC),
                    revision="deadbeef",
                )

        source: CvSourcePort = OverleafCvSource()
        result = source.fetch_source(fetch_request)

        assert isinstance(result, FetchSourceResult)
        assert result.revision == "deadbeef"
