"""Overleaf Git operations: token verification and repository clone/pull."""

from __future__ import annotations

import os
import shlex
import tempfile
from pathlib import Path

from ._git import GitResult, run_git
from .overleaf_errors import (
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafTokenExpired,
    OverleafUnreachable,
)


def _build_git_url(project_id: str, git_host: str) -> str:
    """Build HTTPS Git remote URL for Overleaf project.

    Args:
        project_id: 24-character hex Overleaf project identifier.
        git_host: Git remote hostname (e.g. ``git.overleaf.com``).

    Returns:
        HTTPS Git remote URL string.
    """
    return f"https://{git_host}/{project_id}.git"


def _create_askpass_script(
    token_path: Path,
    *,
    app_data_dir: Path,
) -> Path:
    """Create temporary Git askpass script that outputs Overleaf token.

    Script content cats token file when Git invokes it during
    authentication.

    Args:
        token_path: Path to file containing Overleaf API token.
        app_data_dir: Directory for temporary script.

    Returns:
        Absolute path to created askpass script.

    Raises:
        OSError: If script cannot be written or made executable.
    """
    app_data_dir.mkdir(parents=True, exist_ok=True)
    fd, script_path_str = tempfile.mkstemp(
        dir=str(app_data_dir),
        prefix="git_askpass_",
    )
    os.close(fd)

    script_path = Path(script_path_str)
    content = f"#!/bin/sh\ncat {shlex.quote(str(token_path))}\n"
    _ = script_path.write_text(content, encoding="utf-8")
    _ = script_path.chmod(0o700)

    return script_path


def _raise_on_git_error(result: GitResult) -> None:
    """Map non-zero Git result to typed Overleaf exception.

    Args:
        result: GitResult from subprocess invocation.

    Raises:
        OverleafTokenExpired: Token invalid or expired.
        OverleafProjectNotFound: Project does not exist.
        OverleafRateLimited: Rate limit exceeded.
        OverleafUnreachable: Service unreachable or unknown error.
    """
    if result.returncode == 0:
        return

    stderr = result.stderr

    if "Authentication failed" in stderr or "not authorized" in stderr:
        raise OverleafTokenExpired(detail=stderr)

    if "Repository not found" in stderr or "not found" in stderr:
        raise OverleafProjectNotFound(project_id="", detail=stderr)

    if "Rate limit" in stderr:
        raise OverleafRateLimited(detail=stderr)

    raise OverleafUnreachable(detail=stderr)


def check_token(
    project_id: str,
    git_host: str,
    token_path: Path,
    *,
    app_data_dir: Path,
) -> None:
    """Verify Overleaf Git token has valid access to project.

    Performs ``git ls-remote`` against project remote URL using token as
    credential helper.

    Args:
        project_id: 24-character hex Overleaf project identifier.
        git_host: Git remote hostname.
        token_path: Path to file containing Overleaf API token.
        app_data_dir: Directory for temporary askpass script.

    Raises:
        OverleafTokenExpired: Token invalid or expired.
        OverleafProjectNotFound: Project does not exist.
        OverleafRateLimited: Rate limit exceeded.
        OverleafUnreachable: Service unreachable or unknown error.
    """
    url = _build_git_url(project_id, git_host)
    askpass_script: Path | None = None

    try:
        askpass_script = _create_askpass_script(token_path, app_data_dir=app_data_dir)

        env: dict[str, str] = dict(os.environ)
        env["GIT_ASKPASS"] = str(askpass_script)
        env["GIT_TERMINAL_PROMPT"] = "0"

        result = run_git(["git", "ls-remote", url], env=env)
        _raise_on_git_error(result)
    finally:
        if askpass_script is not None:
            askpass_script.unlink(missing_ok=True)


def clone_or_pull(
    project_id: str,
    git_host: str,
    token_path: Path,
    target_dir: Path,
    *,
    app_data_dir: Path,
) -> str:
    """Clone or pull Overleaf Git repository.

    If ``target_dir`` does not exist or is empty, performs fresh clone.
    Otherwise performs ``git pull`` on existing repository.

    Args:
        project_id: 24-character hex Overleaf project identifier.
        git_host: Git remote hostname.
        token_path: Path to file containing Overleaf API token.
        target_dir: Local directory for repository working tree.
        app_data_dir: Directory for temporary askpass script.

    Returns:
        HEAD revision SHA after operation.

    Raises:
        OverleafTokenExpired: Token invalid or expired.
        OverleafProjectNotFound: Project does not exist.
        OverleafRateLimited: Rate limit exceeded.
        OverleafUnreachable: Service unreachable or unknown error.
    """
    url = _build_git_url(project_id, git_host)
    askpass_script: Path | None = None

    try:
        askpass_script = _create_askpass_script(token_path, app_data_dir=app_data_dir)

        env: dict[str, str] = dict(os.environ)
        env["GIT_ASKPASS"] = str(askpass_script)
        env["GIT_TERMINAL_PROMPT"] = "0"

        if not (target_dir / ".git").exists():
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            clone_result = run_git(
                ["git", "clone", url, str(target_dir)],
                env=env,
            )
            _raise_on_git_error(clone_result)
        else:
            # Try pulling from main branch, fallback to master
            pull_result = run_git(
                ["git", "-C", str(target_dir), "pull", "origin", "main"],
                env=env,
            )
            if (
                pull_result.returncode != 0
                and "couldn't find remote ref" in pull_result.stderr
            ):
                pull_result = run_git(
                    ["git", "-C", str(target_dir), "pull", "origin", "master"],
                    env=env,
                )
            _raise_on_git_error(pull_result)

        head_result = run_git(
            ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
            env=env,
        )
        return head_result.stdout.strip()
    finally:
        if askpass_script is not None:
            askpass_script.unlink(missing_ok=True)
