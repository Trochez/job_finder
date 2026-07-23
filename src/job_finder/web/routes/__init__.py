"""Route controllers for the job_finder dashboard UI."""

from __future__ import annotations

from fastapi import APIRouter  # noqa: TC002

from .audit import router as audit_router
from .checkpoints import router as checkpoints_router
from .cv_source import router as cv_source_router
from .dashboard import router as dashboard_router
from .jobs import router as jobs_router
from .profile_settings import router as profile_settings_router

__all__ = [
    "audit_router",
    "checkpoints_router",
    "cv_source_router",
    "dashboard_router",
    "jobs_router",
    "profile_settings_router",
]


def all_routers() -> tuple[APIRouter, ...]:
    """Return all dashboard route routers for inclusion in the app."""
    return (
        dashboard_router,
        profile_settings_router,
        cv_source_router,
        jobs_router,
        audit_router,
        checkpoints_router,
    )
