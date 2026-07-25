"""CV source route controller.

GET /cv-source — render CV source form
POST /cv-source — save CV source settings, redirect
"""

from __future__ import annotations

import logging
import re
import sqlite3
import traceback
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.responses import Response  # noqa: TC002

from job_finder.adapters.repositories.cv_source import (
    CvSourceSettingsRepository,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from starlette.templating import Jinja2Templates

router = APIRouter()

_OVERLEAF_PROJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$")
_DEFAULT_CANDIDATE_PROFILE_ID = "default"


def _ensure_default_profile(connection: sqlite3.Connection) -> None:
    """Insert the default candidate profile row if absent.

    The cv_source_settings table has a FK to candidate_profiles(profile_id),
    so upsert_settings fails with IntegrityError when no profile row exists.
    INSERT OR IGNORE keeps the call idempotent on repeated POSTs.
    """
    now_utc = datetime.now(UTC).isoformat()
    connection.execute(
        "INSERT OR IGNORE INTO candidate_profiles "
        "(profile_id, candidate_id, active_version_id, timezone_name, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            _DEFAULT_CANDIDATE_PROFILE_ID,
            _DEFAULT_CANDIDATE_PROFILE_ID,
            "",
            "UTC",
            now_utc,
        ),
    )
    connection.commit()


def _get_default_settings() -> dict[str, object]:
    return {
        "active_version": "",
        "renderer_path": "",
        "renderer_type": "local",
        "overleaf_project_id": "",
        "overleaf_token": "",
    }


def _get_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates  # type: ignore[no-any-return]
    return templates


def _flash(request: Request, category: str, message: str) -> None:
    if not hasattr(request.app.state, "flash_store"):
        request.app.state.flash_store = []
    request.app.state.flash_store.append((category, message))


def _load_versions(request: Request) -> list[str]:
    versions = getattr(request.app.state, "profile_versions", None)
    if versions is None:
        return ["v1.0.0", "v1.1.0", "v2.0.0"]
    return list(versions)


def _build_repo_from_deps(request: Request) -> CvSourceSettingsRepository | None:
    deps = getattr(request.app.state, "deps", None)
    if deps is None:
        return None
    connection = getattr(deps, "connection", None)
    if connection is None:
        return None
    return CvSourceSettingsRepository(connection)


def _write_overleaf_token(token_path: Path, token: str) -> None:
    """Write token to filesystem with restricted permissions."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token, encoding="utf-8")
    token_path.chmod(0o600)


def _load_db_settings(request: Request) -> dict[str, object]:
    """Load settings from repository and return as dict, or default."""
    try:
        repo = _build_repo_from_deps(request)
        if repo is None:
            return {}

        settings_record = repo.get_settings(
            candidate_profile_id=_DEFAULT_CANDIDATE_PROFILE_ID,
        )
        if settings_record is None:
            return {}

        overleaf_project_id = settings_record.overleaf_project_id or ""
        return {  # noqa: TRY300
            "active_version": settings_record.active_version or "",
            "renderer_type": settings_record.renderer_type,
            "overleaf_project_id": overleaf_project_id,
        }
    except (sqlite3.ProgrammingError, sqlite3.OperationalError):
        return {}


@router.get("/cv-source", name="cv_source")
async def cv_source_get(request: Request) -> Response:
    """Render CV source settings form."""
    templates = _get_templates(request)
    settings = getattr(request.app.state, "cv_settings", None)
    if settings is None:
        db_settings = _load_db_settings(request)
        settings = {**_get_default_settings(), **db_settings}
        request.app.state.cv_settings = settings

    return templates.TemplateResponse(  # type: ignore[return-value]
        request,
        "cv_source.html",
        {
            "settings": settings,
            "profile_versions": _load_versions(request),
            "active_page": "cv_source",
        },
    )


@router.post("/cv-source", name="cv_source_post")
async def cv_source_post(request: Request) -> Response:  # noqa: C901
    """Save CV source settings from form data."""
    form = await request.form()
    active_version = str(form.get("profile_version", ""))
    renderer_path = str(form.get("renderer_path", ""))
    renderer_type = str(form.get("renderer_type", "local"))
    overleaf_project_id = str(form.get("overleaf_project_id", ""))
    overleaf_token = str(form.get("overleaf_token", ""))

    if renderer_type == "overleaf":
        if not _OVERLEAF_PROJECT_ID_RE.fullmatch(overleaf_project_id):
            _flash(request, "error", "Invalid Overleaf project ID (need 24 hex chars)")
            return RedirectResponse(
                url=request.url_for("cv_source"),
                status_code=303,
            )

        if not overleaf_token:
            _flash(request, "error", "Overleaf token required for overleaf renderer")
            return RedirectResponse(
                url=request.url_for("cv_source"),
                status_code=303,
            )

    try:
        # Token writing for overleaf (if applicable)
        if renderer_type == "overleaf":
            deps = getattr(request.app.state, "deps", None)
            if deps is not None:
                settings_ = getattr(deps, "settings", None)
                if settings_ is not None:
                    secrets_path = getattr(settings_, "secrets_reference_path", None)
                    if secrets_path is not None:
                        token_path = secrets_path / "overleaf_token"
                        _write_overleaf_token(token_path, overleaf_token)

        # Set app state and repo upsert
        settings = {
            "active_version": active_version,
            "renderer_path": renderer_path,
            "renderer_type": renderer_type,
            "overleaf_project_id": overleaf_project_id,
            "overleaf_token": "",
        }
        request.app.state.cv_settings = settings

        try:
            repo = _build_repo_from_deps(request)
            if repo is not None:
                connection = getattr(request.app.state.deps, "connection", None)
                if connection is not None:
                    _ensure_default_profile(connection)
                repo.upsert_settings(
                    renderer_type=renderer_type,
                    overleaf_project_id=overleaf_project_id or None,
                    active_version=active_version or None,
                    candidate_profile_id=_DEFAULT_CANDIDATE_PROFILE_ID,
                )
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            pass

    except Exception as e:
        logger.exception("cv_source_post failed")
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(e),
                "error_type": "internal_error",
                "traceback": traceback.format_exc()
            }
        )

    _flash(request, "success", "CV source settings saved")
    return RedirectResponse(
        url=request.url_for("cv_source"),
        status_code=303,
    )
