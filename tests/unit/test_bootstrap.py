from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_package_imports() -> None:
    package = importlib.import_module("job_finder")
    domain_package = importlib.import_module("job_finder.domain")

    assert package.__package__ == "job_finder"
    assert domain_package.__package__ == "job_finder.domain"


def test_pyproject_declares_strict_python_tooling() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")

    assert 'name = "job-finder"' in pyproject_text
    assert 'requires-python = ">=3.12"' in pyproject_text
    assert '"basedpyright>=1.31.0"' in pyproject_text
    assert '"pytest>=9.0.0"' in pyproject_text
    assert '"ruff>=0.12.0"' in pyproject_text
    assert 'typeCheckingMode = "all"' in pyproject_text
    assert 'include = ["src", "tests"]' in pyproject_text
    assert 'select = ["ALL"]' in pyproject_text
    assert '"--strict-config"' in pyproject_text
    assert '"--strict-markers"' in pyproject_text
