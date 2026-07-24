"""Tests for PrivateSettings with overleaf_config_path field."""

from __future__ import annotations

from pathlib import Path

import pytest

from job_finder.adapters.settings import (
    PrivateSettings,
    UnsafeConfiguration,
)

OVERLEAF_CONFIG_PATH = Path("/home/user/.overleaf/config.yaml")


@pytest.fixture
def app_data_dir(tmp_path: Path) -> Path:
    """Fixture providing an app data directory."""
    return tmp_path


@pytest.fixture
def database_path(app_data_dir: Path) -> Path:
    """Fixture providing a database path inside app_data_dir."""
    return app_data_dir / "job_finder.sqlite3"


@pytest.fixture
def base_settings(
    app_data_dir: Path,
    database_path: Path,
) -> PrivateSettings:
    """Fixture providing a PrivateSettings without overleaf_config_path."""
    return PrivateSettings(
        app_data_dir=app_data_dir,
        sqlite_database_path=database_path,
    )


class TestOverleafConfigPathField:
    """Tests for overleaf_config_path field validation."""

    def test_accepts_valid_path(
        self,
        app_data_dir: Path,
        database_path: Path,
    ) -> None:
        """Absolute path accepted for overleaf_config_path."""
        settings = PrivateSettings(
            app_data_dir=app_data_dir,
            sqlite_database_path=database_path,
            overleaf_config_path=OVERLEAF_CONFIG_PATH,
        )

        assert settings.overleaf_config_path == OVERLEAF_CONFIG_PATH

    def test_rejects_keys_path(
        self,
        app_data_dir: Path,
        database_path: Path,
    ) -> None:
        """Path containing .keys raises UnsafeConfiguration."""
        with pytest.raises(UnsafeConfiguration, match="overleaf_config_path"):
            _ = PrivateSettings(
                app_data_dir=app_data_dir,
                sqlite_database_path=database_path,
                overleaf_config_path=Path("/home/user/.keys/overleaf.yaml"),
            )

    def test_defaults_to_none(self, base_settings: PrivateSettings) -> None:
        """overleaf_config_path defaults to None."""
        assert base_settings.overleaf_config_path is None

    def test_rejects_relative_path(
        self,
        app_data_dir: Path,
        database_path: Path,
    ) -> None:
        """Relative overleaf_config_path raises UnsafeConfiguration."""
        with pytest.raises(UnsafeConfiguration, match="overleaf_config_path"):
            _ = PrivateSettings(
                app_data_dir=app_data_dir,
                sqlite_database_path=database_path,
                overleaf_config_path=Path("relative/config.yaml"),
            )


class TestFromPathsOverleafConfigPath:
    """Tests for from_paths factory with overleaf_config_path."""

    def test_from_paths_accepts_overleaf_config_path(
        self,
        app_data_dir: Path,
    ) -> None:
        """from_paths accepts valid overleaf_config_path."""
        settings = PrivateSettings.from_paths(
            app_data_dir=app_data_dir,
            overleaf_config_path=OVERLEAF_CONFIG_PATH,
        )

        assert settings.overleaf_config_path == OVERLEAF_CONFIG_PATH

    def test_from_paths_rejects_keys_overleaf_config_path(
        self,
        app_data_dir: Path,
    ) -> None:
        """from_paths rejects overleaf_config_path in .keys."""
        with pytest.raises(UnsafeConfiguration, match="overleaf_config_path"):
            _ = PrivateSettings.from_paths(
                app_data_dir=app_data_dir,
                overleaf_config_path=Path("/home/user/.keys/overleaf.yaml"),
            )
