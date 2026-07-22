"""Integration tests for the CV renderer port and local working-tree adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from job_finder.adapters.cv_renderer import (
    EvidenceInsufficient,
    LocalOverleafRenderer,
    RenderRequest,
    RenderResult,
)
from job_finder.domain.ids import CandidateProfileId

if TYPE_CHECKING:
    from pathlib import Path


def test_happy_path_renders_from_fixture_tree(tmp_path: Path) -> None:
    """Given a local working tree with a matching template directory,
    rendering produces a ``RenderResult`` with a deterministic artifact ID
    and the output file exists on disk.
    """
    # ── Arrange ──────────────────────────────────────────────────────────
    working_tree = tmp_path / "overleaf_project"
    template_dir = working_tree / "moderncv"
    template_dir.mkdir(parents=True)
    cls_file = template_dir / "moderncv.cls"
    _ = cls_file.write_text("% dummmy class", encoding="utf-8")

    output_dir = tmp_path / "out"

    renderer = LocalOverleafRenderer(working_tree_path=working_tree)

    request = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-123"),
        template_name="moderncv",
        output_path=output_dir,
        fact_ids=("fact-1", "fact-2"),
    )

    # ── Act ──────────────────────────────────────────────────────────────
    result: RenderResult = renderer.render(request)

    # ── Assert ───────────────────────────────────────────────────────────
    assert isinstance(result.artifact_id, str)
    assert len(result.artifact_id) == 32  # uuid5.hex
    assert result.output_path.name == f"{result.artifact_id}.tex"
    assert result.output_path.is_file()
    assert result.fact_ids_used == ("fact-1", "fact-2")


def test_happy_path_deterministic_artifact_id(tmp_path: Path) -> None:
    """Rendering the same request twice yields the same artifact ID."""
    working_tree = tmp_path / "overleaf_project"
    (working_tree / "simple").mkdir(parents=True)

    renderer = LocalOverleafRenderer(working_tree_path=working_tree)

    request = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-456"),
        template_name="simple",
        output_path=tmp_path / "out1",
        fact_ids=(),
    )

    result_a = renderer.render(request)
    request_same = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-456"),
        template_name="simple",
        output_path=tmp_path / "out2",
        fact_ids=(),
    )
    result_b = renderer.render(request_same)

    assert result_a.artifact_id == result_b.artifact_id


def test_failure_missing_working_tree_raises(tmp_path: Path) -> None:
    """A non-existent working tree raises ``EvidenceInsufficient``."""
    missing_tree = tmp_path / "does_not_exist"
    renderer = LocalOverleafRenderer(working_tree_path=missing_tree)

    request = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-789"),
        template_name="moderncv",
        output_path=tmp_path / "out",
        fact_ids=(),
    )

    with pytest.raises(EvidenceInsufficient) as exc_info:
        _ = renderer.render(request)

    assert "Working tree not found" in str(exc_info.value)


def test_failure_missing_template_raises(tmp_path: Path) -> None:
    """A working tree that lacks the requested template raises
    ``EvidenceInsufficient`` and produces no artifact on disk.
    """
    working_tree = tmp_path / "overleaf_project"
    working_tree.mkdir(parents=True)
    # No template sub-directory created.

    renderer = LocalOverleafRenderer(working_tree_path=working_tree)

    request = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-789"),
        template_name="nonexistent_template",
        output_path=tmp_path / "out",
        fact_ids=(),
    )

    with pytest.raises(EvidenceInsufficient) as exc_info:
        _ = renderer.render(request)

    assert "Template 'nonexistent_template' not found" in str(exc_info.value)


def test_artifact_content_includes_latex_preamble(tmp_path: Path) -> None:
    """The rendered ``.tex`` file contains a documentclass derived from the
    template directory's ``.cls`` file.
    """
    working_tree = tmp_path / "overleaf_project"
    template_dir = working_tree / "customtemplate"
    template_dir.mkdir(parents=True)
    _ = (template_dir / "customtemplate.cls").write_text("% class", encoding="utf-8")

    renderer = LocalOverleafRenderer(working_tree_path=working_tree)
    request = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-111"),
        template_name="customtemplate",
        output_path=tmp_path / "out",
        fact_ids=(),
    )

    result = renderer.render(request)
    content = result.output_path.read_text(encoding="utf-8")

    assert "\\documentclass{customtemplate}" in content
    assert "\\begin{document}" in content
    assert "\\end{document}" in content


def test_rendered_at_is_timezone_aware(tmp_path: Path) -> None:
    """The ``rendered_at`` timestamp carries timezone information (UTC)."""
    working_tree = tmp_path / "project"
    (working_tree / "base").mkdir(parents=True)

    renderer = LocalOverleafRenderer(working_tree_path=working_tree)
    request = RenderRequest(
        candidate_profile_id=CandidateProfileId("candidate-ts"),
        template_name="base",
        output_path=tmp_path / "out",
        fact_ids=(),
    )

    result = renderer.render(request)

    assert result.rendered_at.tzinfo is not None
    assert result.rendered_at.utcoffset() is not None
