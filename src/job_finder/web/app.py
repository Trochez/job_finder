"""FastAPI application factory with dependency wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from job_finder.adapters.cv_renderer.overleaf_config import OverleafConfig
from job_finder.adapters.cv_renderer.overleaf_renderer import OverleafGitRenderer
from job_finder.adapters.cv_renderer.overleaf_source import OverleafGitSource
from job_finder.adapters.db import bootstrap_private_sqlite_storage
from job_finder.adapters.migrations import connect_migrated_sqlite_database
from job_finder.adapters.repositories.workflow import (
    SqliteWorkflowRepository,
)
from job_finder.adapters.settings import PrivateSettings

from .deps import AppDependencies
from .errors import web_error_mapper
from .routes import all_routers

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi.responses import Response

# Module-level hook for test dependency injection.
_test_deps: AppDependencies | None = None

# Template and static directory paths.
_HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = _HERE / "templates"
STATIC_DIR = _HERE / "static"


def inject_test_deps(deps: AppDependencies) -> None:  # noqa: D103
    global _test_deps  # noqa: PLW0603
    _test_deps = deps


def _setup_templates(app: FastAPI) -> Jinja2Templates:
    """Configure Jinja2 templates and attach to app state."""
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    # Register a global function to retrieve flash messages from app state.
    def _get_flashed_messages(_request: Request) -> list[tuple[str, str]]:
        store: list[tuple[str, str]] = getattr(
            app.state, "flash_store", [],
        )
        if hasattr(app.state, "flash_store"):
            app.state.flash_store = []
        return store

    # Register as Jinja2 global for use in base template.
    dict.__setitem__(
        templates.env.globals, "get_flashed_messages", _get_flashed_messages,
    )
    app.state.templates = templates
    return templates


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

    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )

    _setup_templates(app)

    for router in all_routers():
        app.include_router(router)

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

        # Wire Overleaf source and renderer if config path provided
        if settings.overleaf_config_path is not None:
            token_path = (
                settings.secrets_reference_path / "overleaf_token"
                if settings.secrets_reference_path
                else Path("/dev/null")
            )

            overleaf_source = OverleafGitSource()
            overleaf_renderer = OverleafGitRenderer(
                source=overleaf_source,
                overleaf_config=OverleafConfig(
                    project_id="",  # Will be loaded from DB at render time
                    token_path=token_path,
                ),
                cache_dir=settings.app_data_dir / "overleaf_cache",
            )
            deps.overleaf_source = overleaf_source
            deps.overleaf_renderer = overleaf_renderer

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
