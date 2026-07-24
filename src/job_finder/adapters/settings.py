"""Configuration validation and private settings management."""

from __future__ import annotations

import stat
from dataclasses import dataclass
from pathlib import Path
from typing import override

PRIVATE_DIRECTORY_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass(frozen=True, slots=True)
class ConfigurationError(Exception):
    """A configuration field failed validation."""

    field_name: str
    detail: str

    @override
    def __str__(self) -> str:
        return f"{self.field_name}: {self.detail}"


@dataclass(frozen=True, slots=True)
class UnsafeConfiguration(ConfigurationError):  # noqa: N818
    """An unsafe or insecure configuration value was provided."""


@dataclass(frozen=True, slots=True)
class PrivateSettings:
    """Immutable validated private file-system settings."""

    app_data_dir: Path
    sqlite_database_path: Path
    secrets_reference_path: Path | None = None
    overleaf_config_path: Path | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        validated_app_data_dir = _validate_private_directory(
            self.app_data_dir,
            field_name="app_data_dir",
        )
        validated_database_path = _validate_absolute_path(
            self.sqlite_database_path,
            field_name="sqlite_database_path",
        )
        _reject_secret_path_textually(
            validated_database_path,
            field_name="sqlite_database_path",
        )
        _require_child_path(
            parent=validated_app_data_dir,
            child=validated_database_path,
            child_field_name="sqlite_database_path",
        )

        validated_secrets_reference_path: Path | None = None
        if self.secrets_reference_path is not None:
            validated_secrets_reference_path = _validate_absolute_path(
                self.secrets_reference_path,
                field_name="secrets_reference_path",
            )
            _reject_secret_path_textually(
                validated_secrets_reference_path,
                field_name="secrets_reference_path",
            )

        validated_overleaf_config_path: Path | None = None
        if self.overleaf_config_path is not None:
            validated_overleaf_config_path = _validate_absolute_path(
                self.overleaf_config_path,
                field_name="overleaf_config_path",
            )
            _reject_secret_path_textually(
                validated_overleaf_config_path,
                field_name="overleaf_config_path",
            )
        object.__setattr__(self, "app_data_dir", validated_app_data_dir)
        object.__setattr__(self, "sqlite_database_path", validated_database_path)
        object.__setattr__(
            self,
            "secrets_reference_path",
            validated_secrets_reference_path,
        )
        object.__setattr__(
            self,
            "overleaf_config_path",
            validated_overleaf_config_path,
        )

    @classmethod
    def from_paths(
        cls,
        *,
        app_data_dir: Path,
        sqlite_database_name: str = "job_finder.sqlite3",
        secrets_reference_path: Path | None = None,
        overleaf_config_path: Path | None = None,
    ) -> PrivateSettings:
        """Construct a PrivateSettings from a directory and database name."""
        validated_app_data_dir = _validate_private_directory(
            app_data_dir,
            field_name="app_data_dir",
        )
        validated_database_name = _validate_database_name(sqlite_database_name)
        sqlite_database_path = validated_app_data_dir / validated_database_name
        _reject_secret_path_textually(
            sqlite_database_path,
            field_name="sqlite_database_path",
        )

        validated_secrets_reference_path: Path | None = None
        if secrets_reference_path is not None:
            validated_secrets_reference_path = _validate_absolute_path(
                secrets_reference_path,
                field_name="secrets_reference_path",
            )
            _reject_secret_path_textually(
                validated_secrets_reference_path,
                field_name="secrets_reference_path",
            )

        validated_overleaf_config_path: Path | None = None
        if overleaf_config_path is not None:
            validated_overleaf_config_path = _validate_absolute_path(
                overleaf_config_path,
                field_name="overleaf_config_path",
            )
            _reject_secret_path_textually(
                validated_overleaf_config_path,
                field_name="overleaf_config_path",
            )

        return cls(
            app_data_dir=validated_app_data_dir,
            sqlite_database_path=sqlite_database_path,
            secrets_reference_path=validated_secrets_reference_path,
            overleaf_config_path=validated_overleaf_config_path,
        )


def _validate_private_directory(path: Path, *, field_name: str) -> Path:
    validated_path = _validate_absolute_path(path, field_name=field_name)
    _reject_secret_path_textually(validated_path, field_name=field_name)

    if validated_path.exists():
        if not validated_path.is_dir():
            raise UnsafeConfiguration(field_name, "must point to a directory")

        mode = stat.S_IMODE(validated_path.stat().st_mode)
        if mode != PRIVATE_DIRECTORY_MODE:
            raise UnsafeConfiguration(
                field_name,
                "must already be private with mode 0o700",
            )

    return validated_path


def _validate_absolute_path(path: Path, *, field_name: str) -> Path:
    expanded_path = path.expanduser()
    if not expanded_path.is_absolute():
        raise UnsafeConfiguration(field_name, "must be an absolute path")
    return expanded_path


def _validate_database_name(sqlite_database_name: str) -> str:
    if sqlite_database_name in {"", ".", ".."}:
        msg = "sqlite_database_name"
        raise UnsafeConfiguration(
            msg,
            "must be a plain SQLite file name",
        )

    if Path(sqlite_database_name).name != sqlite_database_name:
        msg = "sqlite_database_name"
        raise UnsafeConfiguration(
            msg,
            "must not contain path separators",
        )

    return sqlite_database_name


def _reject_secret_path_textually(path: Path, *, field_name: str) -> None:
    if any(part == ".keys" for part in path.parts):
        raise UnsafeConfiguration(
            field_name,
            "must not reference .keys paths",
        )


def _require_child_path(*, parent: Path, child: Path, child_field_name: str) -> None:
    if child.parent != parent:
        raise UnsafeConfiguration(
            child_field_name,
            "must stay inside app_data_dir",
        )
