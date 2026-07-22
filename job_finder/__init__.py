"""Namespace package shim that re-exports src/job_finder for import convenience."""
from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_SRC_PACKAGE_PATH = Path(__file__).resolve().parent.parent / "src" / __name__
src_package_path = str(_SRC_PACKAGE_PATH)
if src_package_path not in __path__:
    __path__.append(src_package_path)
