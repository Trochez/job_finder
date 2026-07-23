"""Dashboard route controller.

GET /dashboard — render overview with stats
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from starlette.responses import Response  # noqa: TC002

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

router = APIRouter()


def _get_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates  # type: ignore[no-any-return]
    return templates


def _get_stats(request: Request) -> dict[str, object]:
    user_settings = getattr(request.app.state, "user_settings", {})
    daily_cap = (
        user_settings.get("daily_cap", 10) if isinstance(user_settings, dict) else 10
    )
    return {
        "total_jobs": 4,
        "eligible_jobs": 2,
        "submitted_jobs": 1,
        "pending_review": 1,
        "active_checkpoints": 2,
        "todays_applications": 1,
        "daily_cap": daily_cap,
    }


@router.get("/dashboard", name="dashboard")
async def dashboard(request: Request) -> Response:
    """Render dashboard overview with stats."""
    templates = _get_templates(request)
    stats = _get_stats(request)

    return templates.TemplateResponse(  # type: ignore[return-value]
        request,
        "dashboard.html",
        {
            "stats": stats,
            "active_page": "dashboard",
        },
    )
