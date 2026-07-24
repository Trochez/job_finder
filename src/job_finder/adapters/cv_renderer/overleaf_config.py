"""Overleaf Git configuration model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from job_finder.adapters.settings import ConfigurationError, UnsafeConfiguration

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class OverleafConfig:
    """Validated Overleaf project configuration."""

    project_id: str
    token_path: Path
    git_host: str = "git.overleaf.com"

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not re.fullmatch(r"[0-9a-f]{24}", self.project_id):
            raise ConfigurationError(
                field_name="project_id",
                detail="must be a 24-character hex string",
            )

        expanded = self.token_path.expanduser()
        if not expanded.is_absolute():
            raise UnsafeConfiguration(
                field_name="token_path",
                detail="must be an absolute path",
            )
        if any(part == ".keys" for part in expanded.parts):
            raise UnsafeConfiguration(
                field_name="token_path",
                detail="must not reference .keys paths",
            )
        object.__setattr__(self, "token_path", expanded)
