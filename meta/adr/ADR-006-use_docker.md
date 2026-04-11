---
title: "ADR-006: Use Docker for Containerization"
status: "Accepted"
date: "2026-03-31"
tags:
  - "docker"
  - "deployment"
  - "infrastructure"
---

## Context

* **Problem:** Applications need a consistent, reproducible way to be
  packaged and deployed across different environments (local development,
  CI/CD, staging, production). Environment inconsistencies between
  developer machines, CI runners, and production servers cause "works on
  my machine" problems.
* **Constraints:** The containerization approach must support Python
  applications with Poetry-managed dependencies, multi-stage builds for
  small production images, and work across both x86_64 and ARM
  architectures.

## Decision

We will use **Docker** for containerizing Python applications in this
project.

### Key Conventions

* Each deployable application in `apps/` may include a `Dockerfile`.
* Use **multi-stage builds** to keep production images small:
  * **Builder stage:** Install Poetry, resolve dependencies, build wheels.
  * **Runtime stage:** Copy only the built artifacts and runtime
    dependencies.
* Base images should use `python:3.12-slim` (Debian-based slim images)
  for the runtime stage.
* Use `.dockerignore` (provided at the repository root) to exclude
  unnecessary files from the build context.
* Pin base image versions by digest or specific tag for reproducibility.

### Example Multi-Stage Pattern

```dockerfile
# Builder stage
FROM python:3.12-slim AS builder
RUN pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY src/ ./src/
```

## Considered Options

1. **Docker (Chosen):** Industry-standard containerization platform.
    * *Pros:* Universal adoption, excellent tooling, multi-stage build
      support, broad registry ecosystem, works with any CI/CD system.
    * *Cons:* Adds complexity to the development workflow. Docker Desktop
      license requirements for commercial use.
2. **Podman:** Drop-in Docker replacement.
    * *Pros:* Daemonless, rootless by default, Docker CLI compatible.
    * *Cons:* Smaller community, some Docker Compose features may differ.
      Not yet as widely supported in CI/CD platforms.
3. **No containerization:** Deploy directly to VMs or bare metal.
    * *Pros:* Simpler initial setup.
    * *Cons:* Environment inconsistencies, harder to reproduce issues,
      no isolation guarantees.

## Consequences

* **Positive:** Consistent deployment artifacts across all environments.
  Multi-stage builds produce small, secure production images. Easy to
  integrate with any orchestration platform.
* **Negative:** Developers need Docker installed locally. Container
  builds add time to CI/CD pipelines. Debugging inside containers can
  be less convenient than native execution.
* **Future Implications:** Cloud-specific Docker patterns (e.g., ECR
  integration, Lambda container images) are handled by downstream
  blueprints, not this template. See also
  [ADR-013](ADR-013-piwheels_arm_builds.md) for ARM build optimization.
