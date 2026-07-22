"""FastAPI application factory with dependency wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request

from job_finder.adapters.db import bootstrap_private_sqlite_storage
from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.adapters.repositories.workflow import (
    SqliteWorkflowRepository,
)
from job_finder.adapters.settings import PrivateSettings

from .deps import AppDependencies
from .errors import web_error_mapper

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi.responses import Response

# Module-level hook for test dependency injection.
_test_deps: AppDependencies | None = None


def inject_test_deps(deps: AppDependencies) -> None:  # noqa: D103
    global _test_deps  # noqa: PLW0603
    _test_deps = deps


def create_app(
    deps: AppDependencies | None = None,
) -> FastAPI:
    """Build and return a configured FastAPI application instance.

    When *deps* is provided (testing) the application uses those
    dependencies directly.  When *deps* is ``None`` (production) the
    lifespan handler performs real bootstrap.
    """
    if deps is not None:
        inject_test_deps(deps)

    app = FastAPI(
        title="job-finder",
        version="0.1.0",
        lifespan=app_lifespan,
    )

    @app.exception_handler(Exception)
    async def _handle_error(
        request: Request,
        exception: Exception,
    ) -> Response:
        return web_error_mapper(request, exception)

    @app.get("/health")
    async def health(request: Request) -> dict[str, object]:
        deps_: AppDependencies = request.app.state.deps  # type: ignore[no-any-return]
        return {"status": "ok", "live_mcp": deps_.mcp_available}

    return app


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None]:  # type: ignore[misc,valid-type]
    """Async generator lifespan that bootstraps resources on startup."""
    deps = _test_deps
    if deps is None:
        settings = PrivateSettings.from_paths(
            app_data_dir=Path.home() / ".local/share/job-finder",
        )
        _ = bootstrap_private_sqlite_storage(settings)
        connection = connect_migrated_sqlite_database(
            settings.sqlite_database_path,
        )
        deps = AppDependencies(
            settings=settings,
            connection=connection,
            workflow_repo=SqliteWorkflowRepository(connection),
            notifier=_NullNotifier(),
            mcp_available=False,
        )

    app.state.deps = deps
    try:
        yield
    finally:
        deps.shutdown()


class _NullNotifier:
    """No-op notifier used until real Telegram transport is wired."""

    def send_status(
        self, workflow_status: str = "", aggregate_score: int | None = None
    ) -> None:
        """Silently drop the notification."""
