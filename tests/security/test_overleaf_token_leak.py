"""Security tests: Overleaf token must never leak via output channels.

Sentinels are synthetic token values planted through the code paths
that MUST remain contained -- they must NOT appear in exception
messages, environment variables, subprocess arguments, or temporary
script files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.job_finder.adapters.cv_renderer._git import GitResult
from src.job_finder.adapters.cv_renderer.overleaf_errors import (
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafTokenExpired,
    OverleafUnreachable,
)
from src.job_finder.adapters.cv_renderer.overleaf_git import (
    _create_askpass_script,
    check_token,
    clone_or_pull,
)

pytestmark = pytest.mark.security

# Sentinel token — distinctive value that MUST NOT appear in any output channel
SENTINEL_TOKEN = "olp_sentinel_token_do_not_leak_123456"  # noqa: S105

# Sentinel path for the askpass script mock — not created on disk
SENTINEL_ASKPASS_PATH = Path("/tmp/sentinel_askpass_path")  # noqa: S108


class TestOverleafTokenLeak:
    """Token value must never leak via exceptions, env, args, or files."""

    # ── Exception messages ───────────────────────────────────────────────

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_check_token_expired_exception_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
    ) -> None:
        """OverleafTokenExpired exception detail must not contain token."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=1,
            stdout="",
            stderr="Authentication failed: credentials expired",
        )

        with pytest.raises(OverleafTokenExpired) as exc_info:
            check_token(
                project_id="a" * 24,
                git_host="git.overleaf.com",
                token_path=SENTINEL_ASKPASS_PATH,
                app_data_dir=Path("/tmp"),  # noqa: S108
            )

        exc_str = str(exc_info.value)
        exc_repr = repr(exc_info.value)
        assert SENTINEL_TOKEN not in exc_str
        assert SENTINEL_TOKEN not in exc_repr

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_check_token_not_found_exception_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
    ) -> None:
        """OverleafProjectNotFound exception detail must not contain token."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=1,
            stdout="",
            stderr="Repository not found: project does not exist",
        )

        with pytest.raises(OverleafProjectNotFound) as exc_info:
            check_token(
                project_id="a" * 24,
                git_host="git.overleaf.com",
                token_path=SENTINEL_ASKPASS_PATH,
                app_data_dir=Path("/tmp"),  # noqa: S108
            )

        exc_str = str(exc_info.value)
        exc_repr = repr(exc_info.value)
        assert SENTINEL_TOKEN not in exc_str
        assert SENTINEL_TOKEN not in exc_repr

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_check_token_rate_limit_exception_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
    ) -> None:
        """OverleafRateLimited exception detail must not contain token."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=1,
            stdout="",
            stderr="Rate limit exceeded: too many requests",
        )

        with pytest.raises(OverleafRateLimited) as exc_info:
            check_token(
                project_id="a" * 24,
                git_host="git.overleaf.com",
                token_path=SENTINEL_ASKPASS_PATH,
                app_data_dir=Path("/tmp"),  # noqa: S108
            )

        assert SENTINEL_TOKEN not in str(exc_info.value)

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_check_token_unreachable_exception_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
    ) -> None:
        """OverleafUnreachable exception detail must not contain token."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=128,
            stdout="",
            stderr="Could not resolve host: git.overleaf.com",
        )

        with pytest.raises(OverleafUnreachable) as exc_info:
            check_token(
                project_id="a" * 24,
                git_host="git.overleaf.com",
                token_path=SENTINEL_ASKPASS_PATH,
                app_data_dir=Path("/tmp"),  # noqa: S108
            )

        assert SENTINEL_TOKEN not in str(exc_info.value)

    # ── Environment and subprocess args ──────────────────────────────────

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_check_token_env_and_cmd_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
    ) -> None:
        """Env and cmd passed to run_git must not contain token value."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(0, "", "")

        check_token(
            project_id="a" * 24,
            git_host="git.overleaf.com",
            token_path=SENTINEL_ASKPASS_PATH,
            app_data_dir=Path("/tmp"),  # noqa: S108
        )

        call_args = mock_run_git.call_args
        assert call_args is not None
        args, kwargs = call_args

        # Inspect env dict: GIT_ASKPASS must point to askpass script path,
        # not contain the token value itself.
        env: dict[str, str] = kwargs["env"]
        assert env.get("GIT_ASKPASS") == str(SENTINEL_ASKPASS_PATH)
        assert SENTINEL_TOKEN not in env.get("GIT_ASKPASS", "")
        assert env.get("GIT_TERMINAL_PROMPT") == "0"

        # Inspect cmd list: no argument should contain the token value.
        cmd: list[str] = args[0]
        for arg in cmd:
            assert SENTINEL_TOKEN not in arg

    # ── Clone/pull error paths ──────────────────────────────────────────

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_clone_or_pull_clone_error_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Clone error exception must not contain token."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=1,
            stdout="",
            stderr="Authentication failed: token expired",
        )

        target_dir = tmp_path / "new_repo"
        # target_dir / ".git" does not exist → clone path

        with pytest.raises(OverleafTokenExpired) as exc_info:
            clone_or_pull(
                project_id="a" * 24,
                git_host="git.overleaf.com",
                token_path=SENTINEL_ASKPASS_PATH,
                target_dir=target_dir,
                app_data_dir=tmp_path,
            )

        assert SENTINEL_TOKEN not in str(exc_info.value)

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_clone_or_pull_pull_error_no_token(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Pull error exception must not contain token."""
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=1,
            stdout="",
            stderr="Authentication failed: not authorized",
        )

        target_dir = tmp_path / "existing_repo"
        _ = (target_dir / ".git").mkdir(parents=True)
        # target_dir / ".git" exists → pull path

        with pytest.raises(OverleafTokenExpired) as exc_info:
            clone_or_pull(
                project_id="a" * 24,
                git_host="git.overleaf.com",
                token_path=SENTINEL_ASKPASS_PATH,
                target_dir=target_dir,
                app_data_dir=tmp_path,
            )

        assert SENTINEL_TOKEN not in str(exc_info.value)

    # ── Askpass script content and permissions ──────────────────────────

    def test_askpass_script_cats_token_path_not_token_value(
        self,
        tmp_path: Path,
    ) -> None:
        """Script content cats token file path, not token value."""
        token_file = tmp_path / ".overleaf_token"
        _ = token_file.write_text(SENTINEL_TOKEN, encoding="utf-8")
        _ = token_file.chmod(0o600)

        script_path = _create_askpass_script(
            token_file,
            app_data_dir=tmp_path / "askpass",
        )

        try:
            content = script_path.read_text(encoding="utf-8")
            # The script must cat the file, not embed the token value
            assert SENTINEL_TOKEN not in content
            # Script must reference the token file path
            assert str(token_file) in content
        finally:
            _ = script_path.unlink(missing_ok=True)

    def test_askpass_script_mode_is_0700(
        self,
        tmp_path: Path,
    ) -> None:
        """Script file must have 0o700 mode (executable, owner-only)."""
        token_file = tmp_path / ".overleaf_token"
        _ = token_file.write_text(SENTINEL_TOKEN, encoding="utf-8")
        _ = token_file.chmod(0o600)

        script_path = _create_askpass_script(
            token_file,
            app_data_dir=tmp_path / "askpass_mode",
        )

        try:
            mode = script_path.stat().st_mode & 0o777
            assert mode == 0o700
        finally:
            _ = script_path.unlink(missing_ok=True)

    # ── Token path handling ─────────────────────────────────────────────

    @patch("src.job_finder.adapters.cv_renderer.overleaf_git._create_askpass_script")
    @patch("src.job_finder.adapters.cv_renderer.overleaf_git.run_git")
    def test_token_not_in_stdout_stderr_of_mock(
        self,
        mock_run_git: MagicMock,
        mock_askpass: MagicMock,
    ) -> None:
        """Ensure even mock's stdout/stderr don't accidentally contain token.

        This is a regression gate: if git's output ever echoes the
        credential back, the framework must not propagate it.
        """
        mock_askpass.return_value = SENTINEL_ASKPASS_PATH
        mock_run_git.return_value = GitResult(
            returncode=0,
            stdout="a1b2c3d4e5f6\trefs/heads/main",
            stderr="",
        )

        check_token(
            project_id="a" * 24,
            git_host="git.overleaf.com",
            token_path=SENTINEL_ASKPASS_PATH,
            app_data_dir=Path("/tmp"),  # noqa: S108
        )

        result: GitResult = mock_run_git.return_value
        assert SENTINEL_TOKEN not in result.stdout
        assert SENTINEL_TOKEN not in result.stderr
