"""Run-once CLI for the job-finder worker cycle."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast, override


@dataclass(frozen=True, slots=True)
class LockHeldError(Exception):
    """Raised when another worker process holds the lock file."""

    lock_path: str

    @override
    def __str__(self) -> str:
        return f"lock already held at {self.lock_path}"


@dataclass(frozen=True, slots=True)
class CliArguments:
    """Parsed and validated CLI arguments."""

    test_mode: bool = False
    lock_dir: str | None = None


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the run-once command."""
    parser = argparse.ArgumentParser(
        prog="job-finder-worker",
        description="Run the job-finder worker cycle once.",
    )
    _ = parser.add_argument(
        "--test-mode",
        action="store_true",
        default=False,
        help="Use fake dependencies for testing (no real side effects).",
    )
    _ = parser.add_argument(
        "--lock-dir",
        type=str,
        default=None,
        help=(
            "Directory for the lock file. "
            "Defaults to XDG_RUNTIME_DIR or /tmp."
        ),
    )
    return parser


def parse_args(argv: list[str] | None = None) -> CliArguments:
    """Parse and validate CLI arguments."""
    parser = build_parser()
    ns = parser.parse_args(argv)
    return CliArguments(
        test_mode=cast("bool", ns.test_mode),
        lock_dir=cast("str | None", ns.lock_dir),
    )


def _lock_path(lock_dir: str | None) -> Path:
    directory = lock_dir
    if directory is None:
        directory = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return Path(directory) / "job-finder-worker.lock"


def acquire_lock(lock_dir: str | None = None) -> int:
    """Acquire a lock file to prevent concurrent runs.

    Returns the open file descriptor for the lock.
    Raises *LockHeldError* if the lock is already held.
    """
    lock_file = _lock_path(lock_dir)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(
            str(lock_file),
            os.O_CREAT | os.O_EXCL | os.O_RDWR,
            0o644,
        )
    except FileExistsError as exc:
        raise LockHeldError(str(lock_file)) from exc
    return fd


def release_lock(fd: int, lock_dir: str | None = None) -> None:
    """Release the lock file and close the file descriptor."""
    lock_file = _lock_path(lock_dir)
    os.close(fd)
    lock_file.unlink(missing_ok=True)


def run_once(argv: list[str] | None = None) -> int:
    """Execute the run-once cycle.

    Returns 0 on success, 1 on lock conflict, 2 on other errors.
    """
    args = parse_args(argv)

    try:
        lock_fd = acquire_lock(args.lock_dir)
    except LockHeldError:
        return 1

    try:
        if args.test_mode:
            _run_cycle_test_mode()
        else:
            _run_cycle_production()
    except Exception:  # noqa: BLE001
        return 2
    finally:
        release_lock(lock_fd, args.lock_dir)

    return 0


def _run_cycle_test_mode() -> None:
    """Run the worker cycle with fake/test dependencies."""


def _run_cycle_production() -> None:
    """Run the worker cycle with real dependencies."""


if __name__ == "__main__":
    sys.exit(run_once())
