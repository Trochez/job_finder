"""Tests for CV renderer policy gate."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from job_finder.adapters.cv_renderer.port import CvRendererPort
from job_finder.adapters.cv_renderer_policy import (
    CvRendererAccessDeniedError,
    create_cv_renderer,
)


def test_create_cv_renderer_returns_local() -> None:
    local = MagicMock(spec=CvRendererPort)
    overleaf = MagicMock(spec=CvRendererPort)

    result = create_cv_renderer(
        renderer_type="local",
        local_renderer=local,
        overleaf_renderer=overleaf,
    )

    assert result is local


def test_create_cv_renderer_returns_overleaf() -> None:
    local = MagicMock(spec=CvRendererPort)
    overleaf = MagicMock(spec=CvRendererPort)

    result = create_cv_renderer(
        renderer_type="overleaf",
        local_renderer=local,
        overleaf_renderer=overleaf,
    )

    assert result is overleaf


def test_create_cv_renderer_rejects_unknown() -> None:
    local = MagicMock(spec=CvRendererPort)
    overleaf = MagicMock(spec=CvRendererPort)

    with pytest.raises(CvRendererAccessDeniedError, match="unknown"):
        _ = create_cv_renderer(
            renderer_type="unknown",
            local_renderer=local,
            overleaf_renderer=overleaf,
        )


def test_create_cv_renderer_error_holds_renderer_name() -> None:
    local = MagicMock(spec=CvRendererPort)
    overleaf = MagicMock(spec=CvRendererPort)

    with pytest.raises(CvRendererAccessDeniedError) as exc_info:
        _ = create_cv_renderer(
            renderer_type="production",
            local_renderer=local,
            overleaf_renderer=overleaf,
        )

    assert exc_info.value.renderer_name == "production"
    assert "production" in str(exc_info.value)


def test_create_cv_renderer_both_renderers_are_distinct() -> None:
    """Verify local and overleaf return different instances."""
    local = MagicMock(spec=CvRendererPort)
    overleaf = MagicMock(spec=CvRendererPort)

    result_local = create_cv_renderer(
        renderer_type="local",
        local_renderer=local,
        overleaf_renderer=overleaf,
    )
    result_overleaf = create_cv_renderer(
        renderer_type="overleaf",
        local_renderer=local,
        overleaf_renderer=overleaf,
    )

    assert result_local is not result_overleaf
