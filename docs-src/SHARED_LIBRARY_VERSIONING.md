# Shared Library Versioning

> How shared libraries in `libs/` are versioned and consumed within the
> monorepo.

## Overview

Shared libraries follow **Semantic Versioning (SemVer)** as documented in
[ADR-009](https://github.com/{{GITHUB_OWNER}}/{{PROJECT_NAME}}/blob/main/meta/adr/ADR-009-shared_library_versioning.md). This page
provides practical guidance for contributors working with shared libraries.

## Version Format

All library versions use the `MAJOR.MINOR.PATCH` format:

| Component | When to Increment |
| :--- | :--- |
| `MAJOR` | Breaking changes to the public API |
| `MINOR` | New backward-compatible features |
| `PATCH` | Backward-compatible bug fixes |

## Starting a New Library

New libraries start at version `0.1.0`:

```toml
[tool.poetry]
name = "my-lib"
version = "0.1.0"
```

While at `0.x.y`, minor version bumps may include breaking changes (per the
SemVer specification). Version `1.0.0` signals a stable public API.

## Path Dependencies in the Monorepo

Applications consume libraries as **path dependencies**. This means the
application always uses the local source code, and the version number serves
as documentation of the API contract rather than a resolution constraint.

```toml
# In apps/my-app/pyproject.toml
[tool.poetry.dependencies]
my-lib = { path = "../../libs/my-lib", develop = true }
```

The `develop = true` flag installs the library in editable mode so that
changes to the library source are immediately reflected in the application
without reinstalling.

## When to Bump Versions

Even though path dependencies do not enforce version constraints within the
monorepo, bumping the version is important for:

* **Communication** — other contributors can see at a glance what changed
* **External publishing** — if the library is ever published as a package,
  the version becomes a hard contract
* **Changelog tracking** — version bumps should accompany changelog entries

### Guidelines

* **Patch bump** — bug fix, documentation update, or internal refactor with
  no API change
* **Minor bump** — new function, new parameter with a default value, or new
  module added
* **Major bump** — removed or renamed function, changed return type, removed
  parameter, or any change that could break existing callers

## Multi-Repository Considerations

If a library is used across multiple repositories (for example, published to
a private PyPI index), the version becomes a strict contract:

* Consumers pin to a compatible version range (e.g., `^1.2.0`)
* Breaking changes require a major version bump and a migration guide
* Publish releases from a CI pipeline to ensure reproducibility

For monorepo-only libraries, path dependencies are sufficient and no
publishing step is needed.
