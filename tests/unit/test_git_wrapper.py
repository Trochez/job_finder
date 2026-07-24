"""Tests for vendored git subprocess wrapper."""

from __future__ import annotations

from subprocess import CompletedProcess
from unittest.mock import patch

from src.job_finder.adapters.cv_renderer._git import GitResult, run_git


def test_run_git_returns_git_result() -> None:
    """Mock subprocess.run returns CompletedProcess; verify GitResult fields."""
    fake = CompletedProcess(
        args=["git", "status"], returncode=0, stdout="ok", stderr="",
    )

    with patch("subprocess.run", return_value=fake):
        result = run_git(
            ["git", "status"], env={"GIT_DIR": "/tmp"},  # noqa: S108
        )

    assert isinstance(result, GitResult)
    assert result.returncode == 0
    assert result.stdout == "ok"
    assert result.stderr == ""


def test_run_git_captures_stdout() -> None:
    """Stdout from subprocess is exposed as GitResult.stdout."""
    fake = CompletedProcess(
        args=["git", "log", "--oneline", "-1"],
        returncode=0,
        stdout="abc123 commit message\n",
        stderr="",
    )

    with patch("subprocess.run", return_value=fake):
        result = run_git(
            ["git", "log", "--oneline", "-1"],
            env={"GIT_DIR": "/tmp"},  # noqa: S108
        )

    assert result.stdout == "abc123 commit message\n"


def test_run_git_captures_stderr() -> None:
    """Stderr from subprocess is exposed as GitResult.stderr."""
    fake = CompletedProcess(
        args=["git", "status"],
        returncode=128,
        stdout="",
        stderr="fatal: not a git repository",
    )

    with patch("subprocess.run", return_value=fake):
        result = run_git(
            ["git", "status"], env={"GIT_DIR": "/tmp"},  # noqa: S108
        )

    assert result.stderr == "fatal: not a git repository"


def test_run_git_passes_env() -> None:
    """Env dict is forwarded to subprocess.run."""
    expected_env = {"GIT_DIR": "/repo", "GIT_WORK_TREE": "/repo"}

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=["git", "diff"],
            returncode=0,
            stdout="",
            stderr="",
        )
        run_git(["git", "diff"], env=expected_env)

    mock_run.assert_called_once_with(
        ["git", "diff"],
        capture_output=True,
        text=True,
        env=expected_env,
        check=False,
    )
