"""Integration tests for OverleafGitRenderer with a fake CvSourcePort."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import job_finder.adapters.cv_renderer.overleaf_renderer as or_mod
from job_finder.adapters.cv_renderer import (
    CvRendererPort,
    EvidenceInsufficient,
    OverleafGitRenderer,
    RenderRequest,
    RenderResult,
)
from job_finder.adapters.cv_renderer.cv_source_port import (
    FetchSourceRequest,
    FetchSourceResult,
)
from job_finder.adapters.cv_renderer.overleaf_config import OverleafConfig
from job_finder.adapters.cv_renderer.overleaf_errors import (
    OverleafProjectNotFound,
    OverleafSourceError,
    OverleafTokenExpired,
)
from job_finder.domain.ids import CandidateProfileId

if TYPE_CHECKING:
    from collections.abc import Callable

PROJECT_ID = "0123456789abcdef01234567"
TOKEN_PATH = Path("/home/user/.overleaf/token")


# ── Fake CvSourcePort implementations ────────────────────────────────────────


@dataclass
class _FakeOverleafSource:
    """Fake source that seeds a snapshot directory with .tex files.

    ``seed_func`` is called with the snapshot_dir so the test can
    populate whatever file structure is needed before the source
    returns.
    """

    seed_func: Callable[[Path], None] = field(repr=False)
    revision: str = "deadbeef1234567890abcdef1234567890abcdef"

    def fetch_source(self, request: FetchSourceRequest) -> FetchSourceResult:
        """Seed the snapshot_dir and return a result."""
        request.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.seed_func(request.snapshot_dir)
        return FetchSourceResult(
            snapshot_dir=request.snapshot_dir,
            fetched_at=datetime.now(UTC),
            revision=self.revision,
        )


@dataclass
class _FakeFailingSource:
    """Fake source that raises an OverleafSourceError on fetch."""

    error: OverleafSourceError = field(
        default_factory=lambda: OverleafProjectNotFound(project_id=PROJECT_ID),
    )

    def fetch_source(self, request: FetchSourceRequest) -> FetchSourceResult:
        """Raise the configured error."""
        raise self.error


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def overleaf_config() -> OverleafConfig:
    """Fixture providing a valid OverleafConfig."""
    return OverleafConfig(project_id=PROJECT_ID, token_path=TOKEN_PATH)


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Fixture providing a cache directory."""
    return tmp_path / "cv_cache"


def _seed_simple_tex(snapshot_dir: Path) -> None:
    """Seed snapshot with a simple .tex file at root level."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n",
        encoding="utf-8",
    )


def _seed_template_subdir(snapshot_dir: Path) -> None:
    """Seed snapshot with a template sub-directory containing .tex."""
    template_dir = snapshot_dir / "moderncv"
    template_dir.mkdir(parents=True)
    (template_dir / "moderncv.cls").write_text("% class", encoding="utf-8")
    (template_dir / "moderncv.tex").write_text(
        "\\documentclass{moderncv}\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )


def _seed_empty_dir(snapshot_dir: Path) -> None:
    """Seed snapshot with an empty directory (no .tex files)."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Fixture providing an output directory."""
    out = tmp_path / "output"
    out.mkdir(parents=True, exist_ok=True)
    return out


# ── Happy path ───────────────────────────────────────────────────────────────


class TestHappyPath:
    """Tests for successful render scenarios."""

    def test_renders_from_root_tex_file(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """Renderer reads root-level .tex file from snapshot."""
        source = _FakeOverleafSource(seed_func=_seed_simple_tex)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-1"),
            template_name="moderncv",
            output_path=output_dir,
            fact_ids=("fact-1",),
        )

        result = renderer.render(request)

        assert isinstance(result.artifact_id, str)
        assert len(result.artifact_id) == 32
        assert result.output_path.is_file()
        assert result.output_path.read_text(encoding="utf-8") == (
            "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
        )

    def test_renders_from_template_subdir(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """Renderer prefers template-name sub-directory .tex over root."""
        source = _FakeOverleafSource(seed_func=_seed_template_subdir)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-2"),
            template_name="moderncv",
            output_path=output_dir,
            fact_ids=(),
        )

        result = renderer.render(request)

        assert result.output_path.is_file()
        content = result.output_path.read_text(encoding="utf-8")
        assert "\\documentclass{moderncv}" in content

    def test_deterministic_artifact_id(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """Same request yields same artifact ID."""
        source = _FakeOverleafSource(seed_func=_seed_simple_tex)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-3"),
            template_name="base",
            output_path=output_dir,
            fact_ids=("a", "b"),
        )

        result_a = renderer.render(request)
        result_b = renderer.render(request)

        assert result_a.artifact_id == result_b.artifact_id

    def test_rendered_at_is_timezone_aware(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """rendered_at timestamp has UTC timezone info."""
        source = _FakeOverleafSource(seed_func=_seed_simple_tex)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-ts"),
            template_name="base",
            output_path=output_dir,
            fact_ids=(),
        )

        result = renderer.render(request)

        assert result.rendered_at.tzinfo is not None
        assert result.rendered_at.utcoffset() is not None

    def test_fact_ids_preserved(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """fact_ids_used matches the request fact_ids."""
        source = _FakeOverleafSource(seed_func=_seed_simple_tex)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        ids = ("fact-x", "fact-y", "fact-z")
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-fids"),
            template_name="base",
            output_path=output_dir,
            fact_ids=ids,
        )

        result = renderer.render(request)

        assert result.fact_ids_used == ids

    def test_snapshot_dir_cleaned_up(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """Temporary snapshot directory is removed after render."""
        original_mkdtemp = tempfile.mkdtemp

        created_dirs: list[Path] = []

        def tracking_mkdtemp(**kwargs: str) -> str:
            path_str = original_mkdtemp(**kwargs)
            created_dirs.append(Path(path_str))
            return path_str

        original_mkdtemp_mod = or_mod.tempfile.mkdtemp
        or_mod.tempfile.mkdtemp = tracking_mkdtemp  # pyright: ignore[reportAttributeAccessIssue]

        source = _FakeOverleafSource(seed_func=_seed_simple_tex)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-clean"),
            template_name="base",
            output_path=output_dir,
            fact_ids=(),
        )

        try:
            _ = renderer.render(request)
        finally:
            or_mod.tempfile.mkdtemp = original_mkdtemp_mod

        # Verify created temp dirs no longer exist
        for d in created_dirs:
            assert not d.exists(), f"Temp dir not cleaned up: {d}"


# ── Error paths ──────────────────────────────────────────────────────────────


class TestErrorPaths:
    """Tests for error handling in OverleafGitRenderer."""

    def test_source_error_propagates(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """OverleafSourceError from source.fetch_source propagates through render."""
        source = _FakeFailingSource()
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-err"),
            template_name="moderncv",
            output_path=output_dir,
            fact_ids=(),
        )

        with pytest.raises(OverleafProjectNotFound) as exc_info:
            _ = renderer.render(request)

        assert exc_info.value.project_id == PROJECT_ID

    def test_source_error_cleans_up_snapshot(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """Temp snapshot dir is cleaned up even when source raises."""
        snapshot_paths: list[Path] = []

        class _TrackingFailingSource:
            def fetch_source(
                self,
                request: FetchSourceRequest,
            ) -> FetchSourceResult:
                snapshot_paths.append(request.snapshot_dir)
                request.snapshot_dir.mkdir(parents=True, exist_ok=True)
                raise OverleafProjectNotFound(project_id=PROJECT_ID)

        renderer = OverleafGitRenderer(
            source=_TrackingFailingSource(),
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-clean-err"),
            template_name="moderncv",
            output_path=output_dir,
            fact_ids=(),
        )

        with pytest.raises(OverleafProjectNotFound):
            _ = renderer.render(request)

        for p in snapshot_paths:
            assert not p.exists(), f"Snapshot dir not cleaned up: {p}"

    def test_missing_tex_file_raises(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """No .tex files in snapshot raises EvidenceInsufficient."""
        source = _FakeOverleafSource(seed_func=_seed_empty_dir)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-no-tex"),
            template_name="missing",
            output_path=output_dir,
            fact_ids=(),
        )

        with pytest.raises(EvidenceInsufficient) as exc_info:
            _ = renderer.render(request)

        assert "No .tex files found" in str(exc_info.value)

    def test_satisfies_renderer_protocol(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """OverleafGitRenderer satisfies the CvRendererPort protocol."""
        source = _FakeOverleafSource(seed_func=_seed_simple_tex)
        renderer: CvRendererPort = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-proto"),
            template_name="base",
            output_path=output_dir,
            fact_ids=(),
        )

        result = renderer.render(request)

        assert isinstance(result, RenderResult)


class TestErrorPropagation:
    """Tests for error propagation through OverleafGitRenderer."""

    def test_overleaf_source_error_propagates_unchanged(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """OverleafTokenExpired propagates through render, not wrapped."""
        source = _FakeFailingSource(error=OverleafTokenExpired())
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-token-err"),
            template_name="moderncv",
            output_path=output_dir,
            fact_ids=(),
        )

        with pytest.raises(OverleafTokenExpired) as exc_info:
            _ = renderer.render(request)

        assert "Token expired" in str(exc_info.value)
        assert not isinstance(exc_info.value, EvidenceInsufficient)

    def test_missing_template_raises_evidence_insufficient(
        self,
        overleaf_config: OverleafConfig,
        cache_dir: Path,
        output_dir: Path,
    ) -> None:
        """Empty snapshot dir raises EvidenceInsufficient, not OverleafSourceError."""
        source = _FakeOverleafSource(seed_func=_seed_empty_dir)
        renderer = OverleafGitRenderer(
            source=source,
            overleaf_config=overleaf_config,
            cache_dir=cache_dir,
        )
        request = RenderRequest(
            candidate_profile_id=CandidateProfileId("candidate-empty"),
            template_name="missing",
            output_path=output_dir,
            fact_ids=(),
        )

        with pytest.raises(EvidenceInsufficient) as exc_info:
            _ = renderer.render(request)

        assert "No .tex files found" in str(exc_info.value)
        assert not isinstance(exc_info.value, OverleafSourceError)
