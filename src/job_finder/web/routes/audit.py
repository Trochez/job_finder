"""Audit route controller.

GET /audit — render searchable audit evidence history
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from starlette.responses import Response  # noqa: TC002

if TYPE_CHECKING:
    from starlette.templating import Jinja2Templates

router = APIRouter()

STATUS_OPTIONS: tuple[str, ...] = (
    "score",
    "submission",
    "error",
    "checkpoint",
)


def _get_templates(request: Request) -> Jinja2Templates:
    templates: Jinja2Templates = request.app.state.templates  # type: ignore[no-any-return]
    return templates


def _sample_records() -> list[dict[str, object]]:
    return [
        {
            "timestamp": "2026-01-02 03:04:05 UTC",
            "job_id": "job_001",
            "event_type": "score",
            "detail": "Score computed: 85/100 (role_alignment=30, skills_tools=25)",
            "retention_days": 90,
        },
        {
            "timestamp": "2026-01-02 03:05:00 UTC",
            "job_id": "job_002",
            "event_type": "submission",
            "detail": "Application submitted via automated pipeline",
            "retention_days": 90,
        },
        {
            "timestamp": "2026-01-02 03:06:30 UTC",
            "job_id": "job_003",
            "event_type": "error",
            "detail": "Scoring failed: missing candidate profile version",
            "retention_days": 180,
        },
        {
            "timestamp": "2026-01-02 03:07:15 UTC",
            "job_id": "job_001",
            "event_type": "checkpoint",
            "detail": "CAPTCHA challenge detected, pausing workflow",
            "retention_days": None,
        },
    ]


@router.get("/audit", name="audit")
async def audit(request: Request) -> Response:
    """Render audit evidence history with search/filter."""
    templates = _get_templates(request)

    search_query = str(request.query_params.get("search", "")).strip()
    filter_status = str(request.query_params.get("status", "")).strip()

    records = _sample_records()

    if search_query:
        q = search_query.lower()
        records = [
            r
            for r in records
            if q in str(r.get("job_id", "")).lower()
            or q in str(r.get("detail", "")).lower()
        ]

    if filter_status:
        records = [r for r in records if r.get("event_type") == filter_status]

    return templates.TemplateResponse(  # type: ignore[return-value]
        request,
        "audit.html",
        {
            "records": records,
            "search_query": search_query,
            "filter_status": filter_status,
            "status_options": STATUS_OPTIONS,
            "active_page": "audit",
        },
    )
