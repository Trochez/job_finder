import stat
from pathlib import Path

import pytest
from src.job_finder.adapters.db import bootstrap_private_sqlite_storage
from src.job_finder.adapters.settings import PrivateSettings, UnsafeConfiguration


def test_bootstrap_creates_private_sqlite_storage(tmp_path: Path) -> None:
    app_data_dir = tmp_path / "private-app-data"

    settings = PrivateSettings.from_paths(
        app_data_dir=app_data_dir,
        sqlite_database_name="state.sqlite3",
    )

    storage = bootstrap_private_sqlite_storage(settings)

    assert storage.database_path == app_data_dir / "state.sqlite3"
    assert storage.database_path.exists()
    assert stat.S_IMODE(app_data_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(storage.database_path.stat().st_mode) == 0o600


def test_private_settings_reject_secret_file_paths(tmp_path: Path) -> None:
    secret_dir = tmp_path / ".keys" / "job-finder"

    with pytest.raises(UnsafeConfiguration, match=r".keys"):
        _ = PrivateSettings.from_paths(app_data_dir=secret_dir)


def test_private_settings_reject_existing_public_directory(tmp_path: Path) -> None:
    public_dir = tmp_path / "shared-app-data"
    public_dir.mkdir(mode=0o755)

    with pytest.raises(UnsafeConfiguration, match="private"):
        _ = PrivateSettings.from_paths(app_data_dir=public_dir)


def test_private_settings_direct_construction_cannot_escape_app_data_dir(
    tmp_path: Path,
) -> None:
    app_data_dir = tmp_path / "private-app-data"
    outside_database_path = tmp_path / "outside.sqlite3"

    with pytest.raises(UnsafeConfiguration, match="app_data_dir"):
        _ = PrivateSettings(
            app_data_dir=app_data_dir,
            sqlite_database_path=outside_database_path,
        )


def test_private_settings_direct_construction_rejects_secret_database_path(
    tmp_path: Path,
) -> None:
    app_data_dir = tmp_path / "private-app-data"
    secret_database_path = app_data_dir / ".keys" / "state.sqlite3"

    with pytest.raises(UnsafeConfiguration, match=r".keys"):
        _ = PrivateSettings(
            app_data_dir=app_data_dir,
            sqlite_database_path=secret_database_path,
        )
