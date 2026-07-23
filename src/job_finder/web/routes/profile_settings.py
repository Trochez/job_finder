"""Profile settings route controller.

GET /profile-settings — render settings form
POST /profile-settings — save settings, redirect
"""

from __future__ import annotations

import zoneinfo
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response  # noqa: TC002

from job_finder.domain.errors import InvalidTimezoneError
from job_finder.domain.ids import UserTimezone

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

router = APIRouter()

# Hard filter options for the profile settings form
HARD_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("no_remote", "No Remote Work"),
    ("contract_only", "Contract/Freelance Only"),
    ("startup_only", "Startup Only (< 50 employees)"),
    ("requires_relocation", "Requires Relocation"),
    ("below_salary_band", "Below Minimum Salary Band"),
    ("visa_required", "Visa Sponsorship Required"),
)


TIMEZONES: tuple[str, ...] = tuple(sorted(zoneinfo.available_timezones()))


def _get_default_settings() -> dict[str, object]:
    """Return default profile settings."""
    return {
        "timezone": "UTC",
        "hard_filters": [],
        "threshold": 50,
        "daily_cap": 10,
    }


def _get_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates  # type: ignore[no-any-return]
    return templates


def _flash(request: Request, category: str, message: str) -> None:
    if not hasattr(request.app.state, "flash_store"):
        request.app.state.flash_store = []
    request.app.state.flash_store.append((category, message))


@router.get("/profile-settings", name="profile_settings")
async def profile_settings_get(request: Request) -> Response:
    """Render profile settings form with current values."""
    templates = _get_templates(request)
    settings = getattr(request.app.state, "user_settings", None)
    if settings is None:
        settings = _get_default_settings()
        request.app.state.user_settings = settings

    return templates.TemplateResponse(  # type: ignore[return-value]
        request,
        "profile_settings.html",
        {
            "settings": settings,
            "timezones": TIMEZONES,
            "hard_filter_options": HARD_FILTER_OPTIONS,
            "active_page": "profile_settings",
        },
    )


@router.post("/profile-settings", name="profile_settings_post")
async def profile_settings_post(request: Request) -> Response:
    """Save profile settings from form data."""
    form = await request.form()
    timezone_name = str(form.get("timezone", "UTC"))
    hard_filters_raw = form.getlist("hard_filters") if hasattr(form, "getlist") else []
    threshold_str = str(form.get("threshold", "50"))
    daily_cap_str = str(form.get("daily_cap", "10"))

    try:
        _ = UserTimezone.from_name(timezone_name)
    except InvalidTimezoneError:
        _flash(request, "error", f"Invalid timezone: {timezone_name}")
        return RedirectResponse(
            url=request.url_for("profile_settings"),
            status_code=303,
        )

    try:
        threshold = max(0, min(100, int(threshold_str)))
        daily_cap = max(0, min(100, int(daily_cap_str)))
    except (ValueError, TypeError):
        _flash(request, "error", "Threshold and daily cap must be valid numbers")
        return RedirectResponse(
            url=request.url_for("profile_settings"),
            status_code=303,
        )

    # Ensure hard_filters is a list
    if isinstance(hard_filters_raw, str):
        hard_filters_raw = [hard_filters_raw]
    valid_filter_keys = {key for key, _label in HARD_FILTER_OPTIONS}
    hard_filters = [f for f in hard_filters_raw if f in valid_filter_keys]

    settings = {
        "timezone": timezone_name,
        "hard_filters": hard_filters,
        "threshold": threshold,
        "daily_cap": daily_cap,
    }
    request.app.state.user_settings = settings

    _flash(request, "success", "Profile settings saved")
    return RedirectResponse(
        url=request.url_for("profile_settings"),
        status_code=303,
    )
