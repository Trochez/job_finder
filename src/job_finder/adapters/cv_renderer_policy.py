"""Policy gate for CV renderer selection."""

from dataclasses import dataclass
from typing import override

from .cv_renderer.port import CvRendererPort


@dataclass(frozen=True, slots=True)
class CvRendererAccessDeniedError(Exception):  # noqa: D101
    renderer_name: str

    @override
    def __str__(self) -> str:
        return f"Cannot use CV renderer '{self.renderer_name}'"


def create_cv_renderer(  # noqa: D103
    *,
    renderer_type: str,
    local_renderer: CvRendererPort,
    overleaf_renderer: CvRendererPort,
) -> CvRendererPort:
    match renderer_type:
        case "local":
            return local_renderer
        case "overleaf":
            return overleaf_renderer
        case denied:
            raise CvRendererAccessDeniedError(renderer_name=denied)
