"""Job review route controller.

GET /job-review — render scored jobs table
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


def _sample_jobs() -> list[dict[str, object]]:
    return [
        {
            "company": "Acme Corp",
            "title": "Senior Software Engineer",
            "score": 85,
            "eligibility": "eligible",
            "factors": ["role_alignment", "skills_tools", "experience_seniority"],
            "route": "automated",
            "cap_hit": False,
        },
        {
            "company": "Beta Inc",
            "title": "Frontend Developer",
            "score": 62,
            "eligibility": "eligible",
            "factors": ["skills_tools", "domain_relevance"],
            "route": "review",
            "cap_hit": False,
        },
        {
            "company": "Gamma LLC",
            "title": "Data Scientist",
            "score": 35,
            "eligibility": "ineligible",
            "factors": ["domain_relevance"],
            "route": "none",
            "cap_hit": False,
        },
        {
            "company": "Delta Co",
            "title": "DevOps Engineer",
            "score": 72,
            "eligibility": "hard_filter_blocked",
            "factors": ["role_alignment", "skills_tools"],
            "route": "none",
            "cap_hit": True,
        },
    ]


@router.get("/job-review", name="job_review")
async def job_review(request: Request) -> Response:
    """Render scored jobs review table."""
    templates = _get_templates(request)
    jobs = _sample_jobs()

    return templates.TemplateResponse(  # type: ignore[return-value]
        request,
        "job_review.html",
        {
            "jobs": jobs,
            "active_page": "job_review",
        },
    )
