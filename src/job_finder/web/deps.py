"""Typed dependency container for FastAPI application wiring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from collections.abc import Callable

    from job_finder.adapters.notifications.telegram import TelegramNotifierPort
    from job_finder.adapters.repositories.workflow import (
        SqliteWorkflowRepository,
    )
    from job_finder.adapters.settings import PrivateSettings


@dataclass
class AppDependencies:
    """Container for application-scoped dependencies."""

    settings: PrivateSettings
    connection: sqlite3.Connection
    workflow_repo: SqliteWorkflowRepository
    notifier: TelegramNotifierPort
    mcp_available: bool = False
    _cleanup: list[Callable[[], None]] = field(default_factory=list)

    def add_cleanup(self, fn: Callable[[], None]) -> None:
        """Register a cleanup callback called during shutdown."""
        self._cleanup.append(fn)

    def shutdown(self) -> None:
        """Run all registered cleanup callbacks in reverse order."""
        for fn in reversed(self._cleanup):
            fn()
