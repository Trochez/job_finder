"""Checkpoints route controller.

GET /checkpoints — render checkpoint controls
POST /checkpoints — handle checkpoint actions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from starlette.responses import Response  # noqa: TC002

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

router = APIRouter()


def _get_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates  # type: ignore[no-any-return]
    return templates


def _flash(request: Request, category: str, message: str) -> None:
    if not hasattr(request.app.state, "flash_store"):
        request.app.state.flash_store = []
    request.app.state.flash_store.append((category, message))


def _sample_checkpoints() -> list[dict[str, object]]:
    return [
        {
            "checkpoint_id": "cp_001",
            "job_id": "job_001",
            "state": "captcha",
            "created_at": "2026-01-02 03:10:00 UTC",
            "description": "CAPTCHA challenge on Acme Corp application page",
        },
        {
            "checkpoint_id": "cp_002",
            "job_id": "job_004",
            "state": "login_challenge",
            "created_at": "2026-01-02 03:15:00 UTC",
            "description": "Login challenge on Beta Inc careers portal",
        },
    ]


@router.get("/checkpoints", name="checkpoints")
async def checkpoints_get(request: Request) -> Response:
    """Render checkpoints page with active checkpoint cards."""
    templates = _get_templates(request)
    checkpoints = _sample_checkpoints()
    kill_switch_active = getattr(request.app.state, "kill_switch_active", False)

    return templates.TemplateResponse(  # type: ignore[return-value]
        request,
        "checkpoints.html",
        {
            "checkpoints": checkpoints,
            "kill_switch_active": kill_switch_active,
            "active_page": "checkpoints",
        },
    )


@router.post("/checkpoints", name="checkpoints_post")
async def checkpoints_post(request: Request) -> Response:
    """Handle checkpoint actions: resume, answer, dismiss, kill switch."""
    form = await request.form()
    checkpoint_id = str(form.get("checkpoint_id", ""))
    action = str(form.get("action", ""))
    answer = str(form.get("answer", ""))
    kill_switch = form.get("kill_switch")

    if checkpoint_id == "global" and action == "toggle_kill_switch":
        if kill_switch == "1":
            request.app.state.kill_switch_active = True
            _flash(
                request,
                "info",
                "Kill switch activated. All automated processing paused.",
            )
        else:
            request.app.state.kill_switch_active = False
            _flash(request, "success", "Kill switch deactivated. Processing resumed.")
        return RedirectResponse(
            url=request.url_for("checkpoints"),
            status_code=303,
        )

    if action == "resume" and answer:
        _flash(request, "success", f"Answer submitted for checkpoint {checkpoint_id}")
    elif action == "dismiss":
        _flash(request, "info", f"Checkpoint {checkpoint_id} dismissed")
    else:
        _flash(request, "error", f"Unknown action for checkpoint {checkpoint_id}")

    return RedirectResponse(
        url=request.url_for("checkpoints"),
        status_code=303,
    )
