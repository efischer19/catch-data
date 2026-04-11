---
title: "ADR-003: Use Poetry for Dependency Management"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "dependencies"
  - "core-tooling"
---

## Context

* **Problem:** Python projects need a reliable, reproducible way to manage
  dependencies, virtual environments, and package metadata. The standard
  `pip` + `requirements.txt` approach lacks lock files, dependency
  resolution guarantees, and project metadata management.
* **Constraints:** The tool must support monorepo workflows where multiple
  applications and libraries coexist, each with their own dependency trees.
  It must produce reproducible builds and integrate well with CI/CD
  pipelines.

## Decision

We will use **[Poetry](https://python-poetry.org/)** for dependency
management across all Python applications and libraries in this project.

Each application in `apps/` and each library in `libs/` will have its own
`pyproject.toml` managed by Poetry. This provides:

* **Deterministic dependency resolution** via `poetry.lock` files.
* **Standardized project metadata** in `pyproject.toml` (PEP 621
  compatible).
* **Virtual environment management** — Poetry creates and manages
  isolated environments per project.
* **Build and publish support** — Libraries can be built and published
  as Python packages.

### Key Conventions

* Applications **commit** their `poetry.lock` files for reproducible
  deployments.
* Libraries **may** choose to exclude `poetry.lock` from version control
  to test against the latest compatible versions.
* Use `poetry install --no-root` when a project does not need to install
  itself as a package.

## Considered Options

1. **Poetry (Chosen):** Modern dependency management with lock files and
   `pyproject.toml` support.
    * *Pros:* Deterministic builds, excellent dependency resolver, manages
      virtual environments, strong community adoption, `pyproject.toml`
      native.
    * *Cons:* Additional tool to install beyond pip. Occasional slow
      dependency resolution for complex trees.
2. **pip + requirements.txt:** The traditional Python approach.
    * *Pros:* Zero additional tooling, universally understood.
    * *Cons:* No lock file by default, manual virtual environment
      management, no built-in dependency resolution guarantees, scattered
      project metadata.
3. **uv:** Ultra-fast Rust-based Python package manager.
    * *Pros:* Extremely fast dependency resolution, pip-compatible.
    * *Cons:* Newer tool with evolving feature set. May be considered in a
      future ADR as the ecosystem matures.
4. **Pipenv:** Alternative with Pipfile and lock file support.
    * *Pros:* Lock files, virtual environment management.
    * *Cons:* Slower development cadence, less community momentum compared
      to Poetry, does not use `pyproject.toml` for dependency
      specification.

## Consequences

* **Positive:** Reproducible builds across development, CI, and production
  environments. Consistent project structure with `pyproject.toml` as the
  single source of truth for project metadata and dependencies.
* **Negative:** All contributors must install Poetry. Some Docker build
  workflows require extra steps to install Poetry in the build stage.
* **Future Implications:** If uv or another tool demonstrates clear
  advantages, we can evaluate a migration via a new ADR.
