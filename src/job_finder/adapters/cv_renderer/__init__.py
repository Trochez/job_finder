"""CV renderer adapter package for Overleaf artifact generation."""

from .local_renderer import LocalOverleafRenderer
from .overleaf_renderer import OverleafGitRenderer
from .overleaf_source import OverleafGitSource
from .port import (
    CvRendererPort,
    EvidenceInsufficient,
    RenderedArtifactId,
    RenderRequest,
    RenderResult,
)

__all__ = [
    "CvRendererPort",
    "EvidenceInsufficient",
    "LocalOverleafRenderer",
    "OverleafGitRenderer",
    "OverleafGitSource",
    "RenderRequest",
    "RenderResult",
    "RenderedArtifactId",
]
