"""Tests for Overleaf error mapping in WebErrorMapper."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from job_finder.adapters.cv_renderer.overleaf_errors import (
    GitBinaryMissing,
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafTokenExpired,
    OverleafUnreachable,
)
from job_finder.domain.errors import DomainError
from job_finder.web.errors import web_error_mapper

if TYPE_CHECKING:
    from fastapi import Response

    RequestMock = MagicMock


def _parse_body(response: Response) -> dict[str, object]:
    body_bytes = bytes(response.body)  # pyright: ignore[reportArgumentType]
    return dict(json.loads(body_bytes.decode()))


def _assert_error_type(response: Response, expected_type: str) -> None:
    body = _parse_body(response)
    assert body.get("error_type") == expected_type


def test_overleaf_token_expired_maps_to_401(request_mock: RequestMock) -> None:
    exc = OverleafTokenExpired()
    response = web_error_mapper(request_mock, exc)
    assert response.status_code == 401
    _assert_error_type(response, "overleaf_token_expired")


def test_overleaf_project_not_found_maps_to_404(request_mock: RequestMock) -> None:
    exc = OverleafProjectNotFound(project_id="proj_abc")
    response = web_error_mapper(request_mock, exc)
    assert response.status_code == 404
    _assert_error_type(response, "overleaf_project_not_found")


def test_overleaf_rate_limited_maps_to_429(request_mock: RequestMock) -> None:
    exc = OverleafRateLimited()
    response = web_error_mapper(request_mock, exc)
    assert response.status_code == 429
    _assert_error_type(response, "overleaf_rate_limited")


def test_overleaf_unreachable_maps_to_503(request_mock: RequestMock) -> None:
    exc = OverleafUnreachable(detail="Service unreachable")
    response = web_error_mapper(request_mock, exc)
    assert response.status_code == 503
    _assert_error_type(response, "overleaf_unreachable")


def test_git_binary_missing_maps_to_500(request_mock: RequestMock) -> None:
    exc = GitBinaryMissing()
    response = web_error_mapper(request_mock, exc)
    assert response.status_code == 500
    _assert_error_type(response, "git_binary_missing")


def test_overleaf_errors_do_not_mask_domain_errors(request_mock: RequestMock) -> None:
    exc = DomainError()
    response = web_error_mapper(request_mock, exc)
    assert response.status_code == 400
    _assert_error_type(response, "domain_error")


@pytest.fixture
def request_mock() -> MagicMock:
    return MagicMock()
