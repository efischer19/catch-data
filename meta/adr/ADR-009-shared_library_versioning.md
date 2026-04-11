---
title: "ADR-009: Shared Library Versioning Strategy"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "versioning"
  - "libraries"
  - "monorepo"
---

## Context

* **Problem:** Shared libraries in `libs/` are consumed by multiple
  applications. We need a clear versioning strategy that communicates
  compatibility and breaking changes, especially when libraries are used
  as path dependencies within the monorepo or published as packages for
  external consumption.
* **Constraints:** The strategy must work within the monorepo structure
  where applications reference libraries locally, and must also support
  the possibility of publishing libraries as independent packages.

## Decision

We will follow **[Semantic Versioning (SemVer)](https://semver.org/)** for
all shared libraries in `libs/`.

### Version Format: `MAJOR.MINOR.PATCH`

| Component | When to Increment |
| :--- | :--- |
| `MAJOR` | Breaking changes to the public API |
| `MINOR` | New features added in a backward-compatible manner |
| `PATCH` | Bug fixes and minor improvements (backward-compatible) |

### Key Conventions

* Library versions are defined in their `pyproject.toml` under
  `[tool.poetry] version`.
* All libraries start at version `0.1.0` until their API stabilizes.
* While at `0.x.y`, minor version bumps may include breaking changes
  (per SemVer spec).
* Version `1.0.0` signals a stable public API.
* Within the monorepo, applications reference libraries as **path
  dependencies** — the version number serves as documentation of the
  API contract, not as a resolution constraint.
* If a library is published externally, the version becomes a hard
  contract with downstream consumers.
* Version bumps should be accompanied by a changelog entry in the
  library's `README.md` or `CHANGELOG.md`.

### Path Dependency Example

```toml
# In apps/my-app/pyproject.toml
[tool.poetry.dependencies]
my-lib = { path = "../../libs/my-lib", develop = true }
```

## Considered Options

1. **Semantic Versioning (Chosen):** Industry-standard versioning
   convention.
    * *Pros:* Widely understood, communicates intent clearly, works for
      both internal and external consumption.
    * *Cons:* Requires discipline to correctly categorize changes as
      major, minor, or patch.
2. **CalVer (Calendar Versioning):** Version based on release date.
    * *Pros:* Simple, no judgment needed about change severity.
    * *Cons:* Communicates nothing about compatibility or breaking
      changes. Less useful for library consumers.
3. **No formal versioning:** Rely on Git commits for tracking.
    * *Pros:* Zero overhead.
    * *Cons:* No way to communicate API stability or breaking changes.
      Impossible to manage external consumers.

## Consequences

* **Positive:** Clear communication of API stability and compatibility
  across the monorepo. Enables future external publishing of libraries
  without changing the versioning strategy.
* **Negative:** Requires contributors to understand SemVer and correctly
  assess the impact of their changes on library consumers.
* **Future Implications:** As libraries mature past `1.0.0`, breaking
  changes require deliberate major version bumps and potentially
  migration guides.
