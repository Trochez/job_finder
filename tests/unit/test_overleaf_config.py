"""Tests for OverleafConfig frozen dataclass."""

from __future__ import annotations

from pathlib import Path

import pytest

from job_finder.adapters.cv_renderer.overleaf_config import (
    OverleafConfig,
)
from job_finder.adapters.settings import (
    ConfigurationError,
    UnsafeConfiguration,
)

PROJECT_ID = "0123456789abcdef01234567"
TOKEN_PATH = Path("/home/user/.overleaf/token")


def test_valid_config_creates_dataclass() -> None:
    """Happy path: all fields produce a valid OverleafConfig."""
    config = OverleafConfig(project_id=PROJECT_ID, token_path=TOKEN_PATH)

    assert config.project_id == PROJECT_ID
    assert config.token_path == TOKEN_PATH
    assert config.git_host == "git.overleaf.com"


def test_invalid_project_id_raises_error() -> None:
    """Non-hex or wrong-length project_id raises ConfigurationError."""
    with pytest.raises(ConfigurationError, match="project_id"):
        OverleafConfig(project_id="invalid", token_path=TOKEN_PATH)


def test_token_path_not_absolute_raises_error() -> None:
    """Relative token_path raises UnsafeConfiguration."""
    with pytest.raises(UnsafeConfiguration, match="token_path"):
        OverleafConfig(project_id=PROJECT_ID, token_path=Path("relative/path"))


def test_token_path_in_keys_rejected() -> None:
    """Path containing .keys raises UnsafeConfiguration."""
    with pytest.raises(UnsafeConfiguration, match=r"\.keys"):
        OverleafConfig(
            project_id=PROJECT_ID,
            token_path=Path("/home/user/.keys/token"),
        )


def test_default_git_host() -> None:
    """Default git_host is git.overleaf.com."""
    config = OverleafConfig(project_id=PROJECT_ID, token_path=TOKEN_PATH)

    assert config.git_host == "git.overleaf.com"


def test_git_host_custom() -> None:
    """Custom git_host is accepted and stored."""
    config = OverleafConfig(
        project_id=PROJECT_ID,
        token_path=TOKEN_PATH,
        git_host="git.example.com",
    )

    assert config.git_host == "git.example.com"
