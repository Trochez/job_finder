"""Tests for Overleaf Git operations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
from src.job_finder.adapters.cv_renderer._git import GitResult
from src.job_finder.adapters.cv_renderer.overleaf_errors import (
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafTokenExpired,
    OverleafUnreachable,
)
from src.job_finder.adapters.cv_renderer.overleaf_git import (
    _build_git_url,
    check_token,
    clone_or_pull,
)

PREFIX = "src.job_finder.adapters.cv_renderer.overleaf_git"

PROJECT_ID = "0123456789abcdef01234567"
GIT_HOST = "git.overleaf.com"
TOKEN_PATH = Path("/home/user/.overleaf/token")
APP_DATA_DIR = Path("/home/user/app_data")
FAKE_ASKPASS = Path("/home/user/askpass.sh")
SHA_HEX = "a1b2c3d4e5f6789012345678abcdef0123456789"


@pytest.fixture(autouse=True)
def _mock_askpass_and_cleanup() -> Generator[None, None, None]:
    """Prevent real filesystem side effects from askpass script."""
    with (
        patch(f"{PREFIX}._create_askpass_script", return_value=FAKE_ASKPASS),
        patch(f"{PREFIX}.os.unlink"),
    ):
        yield


# ── _build_git_url ────────────────────────────────────────────────────────


def test_build_git_url_returns_https_url() -> None:
    """URL is https://{git_host}/{project_id}.git."""
    url = _build_git_url(PROJECT_ID, GIT_HOST)
    assert url == f"https://{GIT_HOST}/{PROJECT_ID}.git"


# ── check_token ────────────────────────────────────────────────────────────


def test_check_token_success() -> None:
    """Return None when git ls-remote succeeds."""
    with patch(f"{PREFIX}.run_git", return_value=GitResult(0, "", "")):
        result = check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )

    assert result is None


def test_check_token_expired() -> None:
    """Authentication failure raises OverleafTokenExpired."""
    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Authentication failed\n"),
    ), pytest.raises(OverleafTokenExpired):
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )


def test_check_token_expired_not_authorized() -> None:
    """'not authorized' in stderr raises OverleafTokenExpired."""
    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "fatal: not authorized\n"),
    ), pytest.raises(OverleafTokenExpired):
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )


def test_check_token_not_found() -> None:
    """Repository not found raises OverleafProjectNotFound."""
    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Repository not found\n"),
    ), pytest.raises(OverleafProjectNotFound):
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )


def test_check_token_rate_limited() -> None:
    """Rate limit error raises OverleafRateLimited."""
    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Rate limit exceeded\n"),
    ), pytest.raises(OverleafRateLimited):
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )


def test_check_token_unreachable() -> None:
    """Unknown error raises OverleafUnreachable."""
    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Connection refused\n"),
    ), pytest.raises(OverleafUnreachable):
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )


def test_check_token_unreachable_detail() -> None:
    """OverleafUnreachable detail matches full stderr."""
    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Connection timed out\n"),
    ), pytest.raises(OverleafUnreachable) as exc_info:
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )

    assert "Connection timed out" in str(exc_info.value)


def test_check_token_uses_ls_remote_with_correct_url() -> None:
    """check_token calls git ls-remote with https:// URL."""
    expected_url = f"https://{GIT_HOST}/{PROJECT_ID}.git"

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.return_value = GitResult(0, "", "")
        check_token(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, app_data_dir=APP_DATA_DIR,
        )

    cmd = mock_run_git.call_args[0][0]
    assert cmd == ["git", "ls-remote", expected_url]


# ── clone_or_pull ──────────────────────────────────────────────────────────


def test_clone_fresh(tmp_path: Path) -> None:
    """Non-existent target_dir triggers git clone and returns SHA."""
    target = tmp_path / "repo"
    assert not target.exists()

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(0, "Cloning into...\n", ""),
            GitResult(0, f"{SHA_HEX}\n", ""),
        ]
        revision = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    assert revision == SHA_HEX
    clone_cmd = mock_run_git.call_args_list[0].args[0]
    assert clone_cmd[:3] == ["git", "clone", f"https://{GIT_HOST}/{PROJECT_ID}.git"]


def test_pull_existing(tmp_path: Path) -> None:
    """Existing repo with .git triggers git pull and returns SHA."""
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True)

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(0, "Already up to date.\n", ""),
            GitResult(0, f"{SHA_HEX}\n", ""),
        ]
        revision = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    assert revision == SHA_HEX
    pull_cmd = mock_run_git.call_args_list[0].args[0]
    assert pull_cmd == ["git", "-C", str(target), "pull", "origin", "main"]


def test_clone_success_returns_revision(tmp_path: Path) -> None:
    """Clone returns HEAD revision SHA."""
    target = tmp_path / "fresh_repo"

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(0, "Cloning...\n", ""),
            GitResult(0, f"{SHA_HEX}\n", ""),
        ]
        revision = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    assert revision == SHA_HEX
    assert len(revision) == 40


def test_clone_expired(tmp_path: Path) -> None:
    """Clone failure from auth error raises OverleafTokenExpired."""
    target = tmp_path / "expired_repo"

    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Authentication failed\n"),
    ), pytest.raises(OverleafTokenExpired):
        _ = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )


def test_clone_not_found(tmp_path: Path) -> None:
    """Clone failure from missing repo raises OverleafProjectNotFound."""
    target = tmp_path / "missing_repo"

    with patch(
        f"{PREFIX}.run_git",
        return_value=GitResult(128, "", "Repository not found\n"),
    ), pytest.raises(OverleafProjectNotFound):
        _ = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )


def test_pull_updates_revision(tmp_path: Path) -> None:
    """Pull returns new HEAD revision SHA after update."""
    target = tmp_path / "pull_update"
    (target / ".git").mkdir(parents=True)
    new_sha = "fedcba9876543210fedcba9876543210fedcba98"

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(0, "Updating...\n", ""),
            GitResult(0, f"{new_sha}\n", ""),
        ]
        revision = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    assert revision == new_sha


def test_pull_main_branch(tmp_path: Path) -> None:
    """Pull on repo with main branch uses git pull origin main."""
    target = tmp_path / "main_repo"
    (target / ".git").mkdir(parents=True)

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(0, "Already up to date.\n", ""),
            GitResult(0, f"{SHA_HEX}\n", ""),
        ]
        _ = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    # Verify first git call was pull origin main
    first_call = mock_run_git.call_args_list[0]
    assert first_call.args[0] == [
        "git", "-C", str(target), "pull", "origin", "main",
    ]


def test_pull_master_branch(tmp_path: Path) -> None:
    """Pull falls back to master when main branch not found."""
    target = tmp_path / "master_repo"
    (target / ".git").mkdir(parents=True)

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(128, "", "couldn't find remote ref refs/heads/main"),
            GitResult(0, "Already up to date.\n", ""),
            GitResult(0, f"{SHA_HEX}\n", ""),
        ]
        _ = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    calls = mock_run_git.call_args_list
    # First call: pull origin main (failed)
    assert calls[0].args[0] == [
        "git", "-C", str(target), "pull", "origin", "main",
    ]
    # Second call: pull origin master (succeeded)
    assert calls[1].args[0] == [
        "git", "-C", str(target), "pull", "origin", "master",
    ]


def test_clone_constructs_correct_url(tmp_path: Path) -> None:
    """Clone constructs https://{git_host}/{project_id}.git URL."""
    target = tmp_path / "url_check"
    expected_url = f"https://{GIT_HOST}/{PROJECT_ID}.git"

    with patch(f"{PREFIX}.run_git") as mock_run_git:
        mock_run_git.side_effect = [
            GitResult(0, "Cloning...\n", ""),
            GitResult(0, f"{SHA_HEX}\n", ""),
        ]
        _ = clone_or_pull(
            PROJECT_ID, GIT_HOST, TOKEN_PATH, target,
            app_data_dir=APP_DATA_DIR,
        )

    clone_cmd = mock_run_git.call_args_list[0].args[0]
    assert clone_cmd[2] == expected_url
