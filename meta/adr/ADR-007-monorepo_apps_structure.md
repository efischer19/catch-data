---
title: "ADR-007: Monorepo /apps Structure"
status: "Accepted"
date: "2026-03-31"
tags:
  - "architecture"
  - "project-structure"
  - "monorepo"
---

## Context

* **Problem:** As the project grows to include multiple applications and
  shared libraries, we need a clear organizational structure that keeps
  code discoverable, independently deployable, and easy to maintain.
* **Constraints:** The structure must support independent dependency
  management per project (via Poetry), allow shared code reuse, and work
  well with CI/CD pipelines that may build and deploy applications
  independently.

## Decision

We will organize the repository as a **monorepo** with the following
top-level directory structure:

```text
├── apps/          # Standalone, deployable applications
├── libs/          # Shared libraries used across applications
├── testing/       # Shared test utilities and fixtures
├── scripts/       # Automation and utility scripts
├── templates/     # Template files for scaffolding
├── meta/          # ADRs, plans, and project documentation
└── docs-src/      # Documentation source files
```

### Applications (`apps/`)

Each subdirectory in `apps/` is a standalone application with:

* Its own `pyproject.toml` (managed by Poetry)
* Its own `src/` directory for source code
* Its own `tests/` directory for tests
* Its own `Dockerfile` (if containerized)
* Its own `README.md` documenting purpose and usage

Applications are independently buildable, testable, and deployable.

### Libraries (`libs/`)

Each subdirectory in `libs/` is a shared library with:

* Its own `pyproject.toml` (managed by Poetry)
* Its own `src/` directory for source code
* Its own `tests/` directory for tests
* Its own `README.md` documenting the public API

Libraries are consumed by applications as path dependencies or published
packages.

### Shared Testing (`testing/`)

The `testing/` directory contains shared test infrastructure (fixtures,
factories, helpers) that can be used across applications and libraries.

## Considered Options

1. **Monorepo with /apps and /libs (Chosen):** Clear separation between
   deployable applications and reusable libraries.
    * *Pros:* Code discovery is straightforward, shared code is easy to
      reference, atomic cross-cutting changes are possible, single CI/CD
      configuration.
    * *Cons:* Repository size grows over time. CI must be smart about
      which projects to build/test on changes.
2. **Separate repositories per application:** One repo per application
   and library.
    * *Pros:* Clear ownership boundaries, independent release cycles.
    * *Cons:* Cross-cutting changes require coordinated PRs across repos.
      Shared code requires publishing and versioning packages. Higher
      overhead for small projects.
3. **Flat structure:** All code at the repository root.
    * *Pros:* Simple for very small projects.
    * *Cons:* Quickly becomes unmanageable. No clear boundaries between
      applications. Dependency conflicts between projects.

## Consequences

* **Positive:** Clear, predictable structure that scales with the project.
  New applications and libraries follow established patterns. Shared code
  is easily discoverable and reusable.
* **Negative:** Requires discipline to keep applications independent.
  CI/CD pipelines may need path-based filtering to avoid unnecessary
  builds.
* **Future Implications:** As the number of applications grows, we may
  need tooling for managing cross-project dependencies and selective
  builds.
