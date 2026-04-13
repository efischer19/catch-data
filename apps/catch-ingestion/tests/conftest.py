"""Enable shared repository-level pytest fixtures for ingestion tests."""

import sys
from pathlib import Path


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "testing").is_dir() and (candidate / "meta").is_dir():
            return candidate
    raise RuntimeError("Unable to locate repository root")


ROOT = _repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest_plugins = ("testing.conftest",)
