"""Domain-error to HTTP-response mapping for FastAPI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from job_finder.adapters.cv_renderer.overleaf_errors import (
    GitBinaryMissing,
    OverleafProjectNotFound,
    OverleafRateLimited,
    OverleafTokenExpired,
    OverleafUnreachable,
)
from job_finder.adapters.notifications.telegram import TelegramRedactionError
from job_finder.adapters.repositories.workflow import (
    WorkflowTransitionConflictError,
)
from job_finder.adapters.settings import ConfigurationError
from job_finder.domain.errors import DomainError

if TYPE_CHECKING:
    from fastapi import Request, Response


class WebErrorMapper:
    """Maps domain/exceptions to HTTP error responses."""

    def __call__(self, request: Request, exception: Exception) -> Response:  # noqa: ARG002, PLR0911
        """Convert a known exception to a JSON error response."""
        match exception:
            case ConfigurationError() as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": str(exc), "error_type": "configuration_error"},
                )
            case TelegramRedactionError() as exc:
                return JSONResponse(
                    status_code=422,
                    content={"detail": str(exc), "error_type": "redaction_error"},
                )
            case WorkflowTransitionConflictError() as exc:
                return JSONResponse(
                    status_code=409,
                    content={"detail": str(exc), "error_type": "workflow_conflict"},
                )
            case OverleafTokenExpired() as exc:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": str(exc),
                        "error_type": "overleaf_token_expired",
                    },
                )
            case OverleafProjectNotFound() as exc:
                return JSONResponse(
                    status_code=404,
                    content={
                        "detail": str(exc),
                        "error_type": "overleaf_project_not_found",
                    },
                )
            case OverleafRateLimited() as exc:
                return JSONResponse(
                    status_code=429,
                    content={"detail": str(exc), "error_type": "overleaf_rate_limited"},
                )
            case OverleafUnreachable() as exc:
                return JSONResponse(
                    status_code=503,
                    content={"detail": str(exc), "error_type": "overleaf_unreachable"},
                )
            case GitBinaryMissing() as exc:
                return JSONResponse(
                    status_code=500,
                    content={"detail": str(exc), "error_type": "git_binary_missing"},
                )
            case DomainError() as exc:
                return JSONResponse(
                    status_code=400,
                    content={"detail": str(exc), "error_type": "domain_error"},
                )
            case _:
                return JSONResponse(
                    status_code=500,
                    content={
                        "detail": "Internal server error",
                        "error_type": "internal_error",
                    },
                )


web_error_mapper = WebErrorMapper()
