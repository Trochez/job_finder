"""Tests for the run-once CLI entry point."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from src.job_finder.worker.cli import (
    CliArguments,
    LockHeldError,
    acquire_lock,
    build_parser,
    parse_args,
    release_lock,
    run_once,
)


class TestCliParser:
    """Tests for argument parsing."""

    def test_default_args(self) -> None:
        """Default arguments produce a non-test-mode CLI."""
        args: CliArguments = parse_args([])
        assert args.test_mode is False
        assert args.lock_dir is None

    def test_test_mode_flag(self) -> None:
        """The --test-mode flag is parsed correctly."""
        args: CliArguments = parse_args(["--test-mode"])
        assert args.test_mode is True

    def test_lock_dir_option(self) -> None:
        """The --lock-dir option is parsed correctly."""
        args: CliArguments = parse_args(["--lock-dir", "/custom/lock/path"])
        assert args.lock_dir == "/custom/lock/path"

    def test_build_parser_returns_parser(self) -> None:
        """build_parser returns a usable ArgumentParser."""
        parser = build_parser()
        parsed = parser.parse_args(["--test-mode"])
        assert parsed.test_mode is True


class TestRunOnceLock:
    """Tests for the lock-file mechanism."""

    def test_lock_prevents_concurrent_runs(self, tmp_path: Path) -> None:
        """A held lock prevents another run from starting."""
        lock_dir = str(tmp_path)
        held_fd = acquire_lock(lock_dir)
        try:
            exit_code = run_once(["--test-mode", "--lock-dir", lock_dir])
            assert exit_code == 1, "should report lock conflict"
        finally:
            os.close(held_fd)
            (tmp_path / "job-finder-worker.lock").unlink(missing_ok=True)

    def test_lock_held_error_raised(self, tmp_path: Path) -> None:
        """LockHeldError is raised when the lock file exists."""
        lock_dir = str(tmp_path)
        fd = acquire_lock(lock_dir)
        try:
            with pytest.raises(LockHeldError) as exc_info:
                acquire_lock(lock_dir)
            assert "lock already held" in str(exc_info.value)
        finally:
            Path(tmp_path / "job-finder-worker.lock").unlink(missing_ok=True)
            os.close(fd)

    def test_release_clears_lock(self, tmp_path: Path) -> None:
        """Lock is cleared after release, allowing re-acquisition."""
        lock_dir = str(tmp_path)
        fd = acquire_lock(lock_dir)
        release_lock(fd, lock_dir)

        fd2 = acquire_lock(lock_dir)
        release_lock(fd2, lock_dir)
        # No exception means lock was released correctly.

    def test_run_in_test_mode_uses_fakes(self, tmp_path: Path) -> None:
        """Run in test mode does not raise."""
        exit_code = run_once(["--test-mode", "--lock-dir", str(tmp_path)])
        assert exit_code == 0
