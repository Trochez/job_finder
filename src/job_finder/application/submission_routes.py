"""Submission route classification and execution access control.

Determines how a job application should be submitted (easy-apply, external
ATS, or unsupported) and what level of live execution is permitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from job_finder.adapters.cv_renderer.port import (
    RenderedArtifactId,
    RenderRequest,
)

if TYPE_CHECKING:
    from pathlib import Path

    from job_finder.adapters.cv_renderer.port import CvRendererPort
    from job_finder.adapters.mcp.port import JobListing
    from job_finder.domain.ids import CandidateProfileId


# ── enums ────────────────────────────────────────────────────────────────────


@unique
class ApplicationRoute(StrEnum):
    """How a job posting accepts applications."""

    EASY_APPLY = "easy_apply"
    EXTERNAL_ATS = "external_ats"
    UNSUPPORTED = "unsupported"


@unique
class ExecutionAccessState(StrEnum):
    """What level of live execution is allowed for a route."""

    FAKE_ONLY = "fake_only"
    LIVE_ACCESS_BLOCKED = "live_access_blocked"
    ELIGIBLE_FOR_MANUAL_ENABLEMENT = "eligible_for_manual_enablement"
    MANUAL_HANDOFF_REQUIRED = "manual_handoff_required"


# ── access record ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ExecutionAccess:
    """The outcome of route preparation for a single job listing.

    Attributes:
        route: The classified application route.
        access_state: The level of live execution permitted.
        rendered_artifact_ref: The rendered CV artifact ID bound during
            preparation, or ``None`` if no artifact was produced.
    """

    route: ApplicationRoute
    access_state: ExecutionAccessState
    rendered_artifact_ref: RenderedArtifactId | None


# ── classification ───────────────────────────────────────────────────────────


_EASY_APPLY_DOMAINS: frozenset[str] = frozenset({
    "linkedin.com",
    "www.linkedin.com",
})

_KNOWN_ATS_DOMAINS: frozenset[str] = frozenset({
    "boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.smartrecruiters.com",
    "myworkdayjobs.com",
    "careers.workday.com",
    "apply.workable.com",
    "jobs.jobvite.com",
    "recruitee.com",
    "wellfound.com",
    "angel.co",
})


def classify_route(job_listing: JobListing) -> ApplicationRoute:
    """Classify a job listing into an ``ApplicationRoute``.

    The classification is based on the listing's ``apply_url``:

    - **easy_apply**: URLs hosted on LinkedIn domains.
    - **external_ats**: URLs hosted on known ATS platforms.
    - **unsupported**: Everything else.
    """
    url = job_listing.evidence.apply_url

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
    except Exception:  # noqa: BLE001 — broad-except for malformed URLs
        return ApplicationRoute.UNSUPPORTED

    if hostname in _EASY_APPLY_DOMAINS:
        return ApplicationRoute.EASY_APPLY

    if hostname in _KNOWN_ATS_DOMAINS:
        return ApplicationRoute.EXTERNAL_ATS

    return ApplicationRoute.UNSUPPORTED


# ── route preparation ────────────────────────────────────────────────────────


def prepare_route(
    route: ApplicationRoute,
    renderer: CvRendererPort,
    *,
    candidate_profile_id: CandidateProfileId,
    output_path: Path,
) -> ExecutionAccess:
    """Prepare an ``ExecutionAccess`` for the given route.

    All routes are presently prepared as **fake_only** with
    **live_access_blocked**.  A CV artifact is always rendered and bound to
    the access record so that fake-attempt flow has the rendered payload
    available.

    Args:
        route: The classified route.
        renderer: The CV renderer to produce the artifact.
        candidate_profile_id: The candidate whose CV should be rendered.
        output_path: Directory where the rendered artifact will be written.

    Returns:
        An ``ExecutionAccess`` record with the rendered artifact ref.

    Raises:
        EvidenceInsufficient: When the renderer cannot locate required
            templates or working tree.
    """
    render_request = RenderRequest(
        candidate_profile_id=candidate_profile_id,
        template_name="moderncv",
        output_path=output_path,
        fact_ids=(),
    )

    result = renderer.render(render_request)
    artifact_ref = result.artifact_id

    return ExecutionAccess(
        route=route,
        access_state=ExecutionAccessState.FAKE_ONLY,
        rendered_artifact_ref=artifact_ref,
    )
