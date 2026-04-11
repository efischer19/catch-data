---
title: "ADR-013: Use Piwheels for ARM Docker Builds"
status: "Accepted"
date: "2026-03-31"
tags:
  - "docker"
  - "arm"
  - "performance"
  - "builds"
---

## Context

* **Problem:** Building Docker images for ARM architectures (e.g.,
  Raspberry Pi, AWS Graviton, Apple Silicon) often requires compiling
  Python C extensions from source, which is significantly slower than
  installing pre-built wheels. This increases build times from minutes
  to tens of minutes or more, especially for packages with heavy native
  dependencies (numpy, pandas, cryptography, etc.).
* **Constraints:** The solution must not affect x86_64 builds, must work
  with standard pip/Poetry workflows, and must not require vendoring or
  maintaining custom package builds.

## Decision

We will use **[piwheels](https://www.piwheels.org/)** as an additional
Python package index for ARM Docker builds to avoid compiling C extensions
from source.

### What is Piwheels?

Piwheels is a community-maintained Python package repository that provides
pre-compiled ARM wheel files. It mirrors PyPI but with wheels built for
ARM architectures (armv7l, aarch64), drastically reducing installation
time for packages with C extensions.

### Key Conventions

* Add piwheels as an **extra index URL** only in ARM Dockerfiles or
  ARM-specific build stages.
* Do **not** add piwheels to `pyproject.toml` or development
  configurations — it is only needed at Docker build time for ARM
  targets.
* Use `--extra-index-url` rather than replacing the primary PyPI index.
* Comment the usage clearly so future contributors understand the
  purpose.

### Example in Dockerfile

```dockerfile
# ARM build optimization: use piwheels for pre-built ARM wheels
ARG TARGETARCH
RUN if [ "$TARGETARCH" = "arm64" ] || [ "$TARGETARCH" = "arm" ]; then \
      pip install --extra-index-url https://www.piwheels.org/simple ...; \
    else \
      pip install ...; \
    fi
```

### Alternative: Conditional pip.conf

```dockerfile
# For ARM-only Dockerfiles
RUN echo "[global]\nextra-index-url = https://www.piwheels.org/simple" \
    > /etc/pip.conf
```

## Considered Options

1. **Piwheels (Chosen):** Pre-built ARM wheels from a community
   repository.
    * *Pros:* Dramatic build time reduction for ARM, no code changes
      required, maintained by the Raspberry Pi community, free to use,
      mirrors PyPI package names.
    * *Cons:* Additional external dependency. May lag behind PyPI for
      very new package versions. Only useful for ARM architectures.
2. **Cross-compilation with QEMU:** Emulate ARM on x86_64 build hosts.
    * *Pros:* No extra package sources needed.
    * *Cons:* Very slow (emulation overhead), unreliable for complex
      builds.
3. **Native ARM build hosts:** Build directly on ARM hardware or VMs.
    * *Pros:* Native speed, no compatibility concerns.
    * *Cons:* Requires ARM CI/CD infrastructure, higher cost, limited
      availability in some CI platforms.
4. **Vendored wheels:** Pre-build and commit ARM wheels to the
   repository.
    * *Pros:* Fully reproducible, no external dependency at build time.
    * *Cons:* Large binary files in version control, maintenance burden
      for every dependency update.

## Consequences

* **Positive:** ARM Docker builds complete in a fraction of the time.
  No changes to application code or dependency specifications. Works
  with existing Poetry/pip workflows.
* **Negative:** Adds an external dependency on the piwheels service.
  Packages may occasionally be unavailable or slightly behind PyPI.
* **Future Implications:** As ARM adoption grows and PyPI adds more
  native ARM wheels, the need for piwheels may diminish over time.
  This ADR can be superseded when ARM wheel coverage on PyPI is
  sufficient.
