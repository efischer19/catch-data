"""Enable shared repository-level pytest fixtures for ingestion tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest_plugins = ("testing.conftest",)
