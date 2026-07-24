"""Tests for Overleaf error hierarchy."""

from __future__ import annotations

import pytest

from job_finder.adapters.cv_renderer.overleaf_errors import (
    GitBinaryMissing,
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafSourceError,
    OverleafTokenExpired,
    OverleafUnreachable,
)


def test_overleaf_token_expired_instantiation() -> None:
    err = OverleafTokenExpired()
    assert err.detail == "Token expired or invalid"


def test_overleaf_project_not_found_instantiation() -> None:
    err = OverleafProjectNotFound(project_id="proj_abc123")
    assert err.project_id == "proj_abc123"
    assert err.detail == "Project not found"


def test_overleaf_rate_limited_instantiation() -> None:
    err = OverleafRateLimited()
    assert err.detail == "Rate limited"


def test_overleaf_unreachable_instantiation() -> None:
    err = OverleafUnreachable(detail="Connection refused")
    assert err.detail == "Connection refused"


def test_git_binary_missing_instantiation() -> None:
    err = GitBinaryMissing()
    assert "git binary required" in err.detail


def test_str_returns_detail() -> None:
    assert str(OverleafTokenExpired()) == "Token expired or invalid"
    assert (
        str(OverleafProjectNotFound(project_id="x"))
        == "Project not found"
    )
    assert str(OverleafRateLimited()) == "Rate limited"
    assert (
        str(OverleafUnreachable(detail="custom msg"))
        == "custom msg"
    )
    assert "git binary required" in str(GitBinaryMissing())


def test_all_are_overleaf_source_error_subclasses() -> None:
    assert issubclass(OverleafTokenExpired, OverleafSourceError)
    assert issubclass(OverleafProjectNotFound, OverleafSourceError)
    assert issubclass(OverleafRateLimited, OverleafSourceError)
    assert issubclass(OverleafUnreachable, OverleafSourceError)
    assert issubclass(GitBinaryMissing, OverleafSourceError)

    assert isinstance(OverleafTokenExpired(), OverleafSourceError)
    assert isinstance(
        OverleafProjectNotFound(project_id="x"), OverleafSourceError
    )
    assert isinstance(OverleafRateLimited(), OverleafSourceError)
    assert isinstance(
        OverleafUnreachable(detail="x"), OverleafSourceError
    )
    assert isinstance(GitBinaryMissing(), OverleafSourceError)


@pytest.mark.parametrize(
    ("exc_cls", "kwargs"),
    [
        (OverleafTokenExpired, {}),
        (OverleafProjectNotFound, {"project_id": "p1"}),
        (OverleafRateLimited, {}),
        (OverleafUnreachable, {"detail": "timeout"}),
        (GitBinaryMissing, {}),
    ],
)
def test_all_exceptions_are_frozen(
    exc_cls: type[OverleafSourceError],
    kwargs: dict[str, object],
) -> None:
    """Verify all exceptions are frozen dataclasses."""
    err = exc_cls(**kwargs)
    with pytest.raises(AttributeError, match=r"cannot assign|frozen"):
        err.detail = "mutated"  # pyright: ignore[reportAttributeAccessIssue]
