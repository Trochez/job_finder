"""Contract tests for CV renderer policy gate selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_finder.adapters.cv_renderer.port import (
    RenderedArtifactId,
    RenderRequest,
    RenderResult,
)
from job_finder.adapters.cv_renderer_policy import (
    CvRendererAccessDeniedError,
    create_cv_renderer,
)

# ── Fake CvRendererPort implementations (duck-typed) ───────────────────────


@dataclass
class _FakeLocalRenderer:
    """Inline fake CvRendererPort — local variant."""

    name: str = "local"

    def render(self, request: RenderRequest) -> RenderResult:
        """Return a minimal RenderResult."""
        return RenderResult(
            artifact_id=RenderedArtifactId("local-artifact"),
            output_path=Path("/dev/null"),
            rendered_at=datetime(2026, 7, 23, tzinfo=UTC),
            fact_ids_used=request.fact_ids,
        )


@dataclass
class _FakeOverleafRenderer:
    """Inline fake CvRendererPort — overleaf variant."""

    name: str = "overleaf"

    def render(self, request: RenderRequest) -> RenderResult:
        """Return a minimal RenderResult."""
        return RenderResult(
            artifact_id=RenderedArtifactId("overleaf-artifact"),
            output_path=Path("/dev/null"),
            rendered_at=datetime(2026, 7, 23, tzinfo=UTC),
            fact_ids_used=request.fact_ids,
        )


# ── Tests ──────────────────────────────────────────────────────────────────


class TestCreateCvRenderer:
    """Contract tests for create_cv_renderer policy gate."""

    def test_create_cv_renderer_returns_local_for_local_type(self) -> None:
        """renderer_type='local' returns the local_renderer instance."""
        local = _FakeLocalRenderer()
        overleaf = _FakeOverleafRenderer()

        result = create_cv_renderer(
            renderer_type="local",
            local_renderer=local,
            overleaf_renderer=overleaf,
        )

        assert result is local

    def test_create_cv_renderer_returns_overleaf_for_overleaf_type(self) -> None:
        """renderer_type='overleaf' returns the overleaf_renderer instance."""
        local = _FakeLocalRenderer()
        overleaf = _FakeOverleafRenderer()

        result = create_cv_renderer(
            renderer_type="overleaf",
            local_renderer=local,
            overleaf_renderer=overleaf,
        )

        assert result is overleaf

    def test_create_cv_renderer_rejects_unknown_type(self) -> None:
        """Unknown renderer_type raises CvRendererAccessDeniedError."""
        local = _FakeLocalRenderer()
        overleaf = _FakeOverleafRenderer()

        with pytest.raises(
            CvRendererAccessDeniedError,
            match="Cannot use CV renderer 'unknown'",
        ) as exc_info:
            _ = create_cv_renderer(
                renderer_type="unknown",
                local_renderer=local,
                overleaf_renderer=overleaf,
            )

        assert exc_info.value.renderer_name == "unknown"

    def test_cv_renderer_access_denied_error_message(self) -> None:
        """CvRendererAccessDeniedError renders correct error message."""
        err = CvRendererAccessDeniedError(renderer_name="badger")

        msg = str(err)

        assert msg == "Cannot use CV renderer 'badger'"

    def test_create_cv_renderer_returns_distinct_instances(self) -> None:
        """Each renderer_type returns its own distinct instance."""
        local_a = _FakeLocalRenderer()
        local_b = _FakeLocalRenderer()
        overleaf = _FakeOverleafRenderer()

        result_a = create_cv_renderer(
            renderer_type="local",
            local_renderer=local_a,
            overleaf_renderer=overleaf,
        )
        result_b = create_cv_renderer(
            renderer_type="local",
            local_renderer=local_b,
            overleaf_renderer=overleaf,
        )
        result_c = create_cv_renderer(
            renderer_type="overleaf",
            local_renderer=local_a,
            overleaf_renderer=overleaf,
        )

        assert result_a is local_a
        assert result_b is local_b
        assert result_c is overleaf
        assert result_a is not result_b
        assert result_b is not result_c
        assert result_a is not result_c
