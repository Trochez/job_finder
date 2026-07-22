"""Re-export all public symbols from the src application package."""
from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

_SRC_PACKAGE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "src" / "job_finder" / "application"
)
src_package_path = str(_SRC_PACKAGE_PATH)
if src_package_path not in __path__:
    __path__.append(src_package_path)

from src.job_finder.application import *  # noqa: F403, E402
