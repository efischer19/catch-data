#!/usr/bin/env python3
"""Install local dependencies across the monorepo.

Walks through all apps/ and libs/ directories that contain a pyproject.toml
and runs ``poetry install`` in each one. This ensures every project has its
dependencies (including path dependencies on sibling libraries) installed
and ready for development.

Usage:
    python scripts/setup-local-deps.py
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECT_DIRS = ["libs", "apps"]


def find_projects() -> list[Path]:
    """Return directories under apps/ and libs/ that contain a pyproject.toml.

    Libraries are returned before applications so that path dependencies
    are installed first.
    """
    projects: list[Path] = []
    for parent in PROJECT_DIRS:
        parent_path = REPO_ROOT / parent
        if not parent_path.is_dir():
            continue
        for child in sorted(parent_path.iterdir()):
            if child.is_dir() and (child / "pyproject.toml").exists():
                projects.append(child)
    return projects


def install_project(project: Path) -> bool:
    """Run ``poetry install`` in *project*. Return True on success."""
    relative = project.relative_to(REPO_ROOT)
    print(f"\n▶ Installing {relative} ...")
    result = subprocess.run(
        ["poetry", "install"],
        cwd=project,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Failed to install {relative}")
        print(result.stdout)
        print(result.stderr)
        return False
    print(f"  ✅ {relative} installed")
    return True


def main() -> None:
    projects = find_projects()
    if not projects:
        print("No projects found in apps/ or libs/.")
        return

    print(f"Found {len(projects)} project(s) to install:")
    for p in projects:
        print(f"  * {p.relative_to(REPO_ROOT)}")

    failures: list[Path] = []
    for project in projects:
        if not install_project(project):
            failures.append(project)

    print()
    if failures:
        print("❌ Some projects failed to install:")
        for f in failures:
            print(f"  * {f.relative_to(REPO_ROOT)}")
        sys.exit(1)
    else:
        print("✅ All projects installed successfully.")


if __name__ == "__main__":
    main()
