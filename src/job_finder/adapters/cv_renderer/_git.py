"""Vendored git subprocess wrapper — single point of git invocation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GitResult:
    """Structured result of a git subprocess invocation."""

    returncode: int
    stdout: str
    stderr: str


def run_git(cmd: list[str], *, env: dict[str, str]) -> GitResult:
    """Execute a git command and return structured result.

    Single point of subprocess invocation. All git calls go through this.
    """
    result = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, env=env, check=False,
    )
    return GitResult(result.returncode, result.stdout, result.stderr)
