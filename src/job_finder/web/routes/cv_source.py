"""CV source route controller.

GET /cv-source — render CV source form
POST /cv-source — save CV source settings, redirect
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response  # noqa: TC002

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

router = APIRouter()


def _get_default_settings() -> dict[str, object]:
    return {
        "active_version": "",
        "renderer_path": "",
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


@router.get("/cv-source", name="cv_source")
async def cv_source_get(request: Request) -> Response:
    """Render CV source settings form."""
    templates = _get_templates(request)
    settings = getattr(request.app.state, "cv_settings", None)
    if settings is None:
        settings = _get_default_settings()
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
async def cv_source_post(request: Request) -> Response:
    """Save CV source settings from form data."""
    form = await request.form()
    active_version = str(form.get("profile_version", ""))
    renderer_path = str(form.get("renderer_path", ""))

    settings = {
        "active_version": active_version,
        "renderer_path": renderer_path,
    }
    request.app.state.cv_settings = settings

    _flash(request, "success", "CV source settings saved")
    return RedirectResponse(
        url=request.url_for("cv_source"),
        status_code=303,
    )
