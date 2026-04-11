---
title: "ADR-014: CI/CD Strategy for Python Monorepo"
status: "Accepted"
date: "2026-04-01"
tags:
  - "ci-cd"
  - "github-actions"
  - "docker"
  - "pypi"
---

## Context

* **Problem:** The monorepo template needs a CI/CD strategy that
  validates code quality, runs tests, demonstrates packaging for PyPI,
  and builds Docker images — while remaining simple enough to serve as a
  learning blueprint for downstream projects.
* **Constraints:** The strategy must work with the existing Poetry-based
  dependency management (ADR-003), use pytest for tests (ADR-004), use
  Ruff for linting (ADR-005), and support Docker-based deployment
  (ADR-006). It must not require credentials for external registries in
  the template repository itself.

## Decision

We will use **GitHub Actions** to implement a multi-workflow CI/CD
pipeline with the following components:

### Reusable Composite Action (`setup-python-poetry`)

A composite action at `.github/actions/setup-python-poetry/action.yml`
standardizes Python and Poetry setup across all workflows. It:

* Installs the specified Python version via `actions/setup-python`
* Installs Poetry via `pip`
* Configures in-project virtual environments (`virtualenvs.in-project true`)
* Caches the `.venv` directory keyed on `os + python-version + poetry.lock hash`

### Continuous Integration (`ci.yml`)

Runs on every pull request and push to `main`. Jobs include:

* **Quality checks:** Pre-commit hooks (formatting, YAML/JSON/TOML
  validation, trailing whitespace, etc.)
* **ADR status check:** Blocks merging of `Proposed` ADRs to `main`
* **Markdown lint:** Validates all Markdown files
* **Python checks (matrix):** For each app and lib —
  `ruff format --check`, `ruff check`, and `pytest`

### PyPI Publish (`publish.yml`)

Runs on version tags (`v*`) or manual dispatch. It:

* Builds the package with `poetry build`
* Includes the `poetry publish` step **commented out** with clear
  instructions for enabling it
* Requires a `PYPI_TOKEN` repository secret to activate publishing

### Docker Build (`build-docker.yml`)

Runs on every pull request and push to `main`. It:

* Builds Docker images for all apps with a `Dockerfile` using
  multi-stage builds (ADR-006)
* Saves images with `docker save | gzip` and uploads them as
  GitHub Actions artifacts (7-day retention)
* Does **not** push to any registry — comments show how to add push
  steps for ECR or Docker Hub

### Documentation (`documentation.yml`)

Runs on every pull request and push to `main`. It:

* Installs MkDocs and `mkdocs-material` from `docs-requirements.txt`
* Builds the docs site with `mkdocs build --strict`
* Deploys to GitHub Pages via `mkdocs gh-deploy --force` on
  pushes to `main` only

### Dependabot Configuration

`.github/dependabot.yml` is configured to monitor:

* `github-actions` — weekly, with grouped PRs
* `pip` — weekly, for each `apps/` and `libs/` subdirectory

## Considered Options

1. **GitHub Actions with reusable composite action (Chosen):** A
   multi-workflow setup using a local composite action for Python/Poetry.
    * *Pros:* Native GitHub integration, no additional secrets needed for
      the template, composite action avoids duplication, caching keeps
      jobs fast, artifacts allow Docker image inspection without a registry.
    * *Cons:* GitHub Actions-specific; switching CI providers would
      require rewriting workflows.
2. **Single monolithic workflow:** One large CI workflow covering all
   jobs.
    * *Pros:* Simpler to read at a glance.
    * *Cons:* Harder to re-run individual failing jobs, no separation
      of concerns between CI and publishing.
3. **External CI (CircleCI, Jenkins, etc.):** Dedicated CI platform.
    * *Pros:* More powerful caching and parallelism options.
    * *Cons:* Additional cost and infrastructure to maintain. The
      template target audience is GitHub users.

## Consequences

* **Positive:** New contributors get immediate feedback on code quality
  and test failures. The publish and Docker workflows demonstrate the
  full lifecycle without requiring real credentials. Caching keeps CI
  fast even for larger projects.
* **Negative:** The commented-out publish step requires manual
  activation; contributors must read the comments to enable publishing.
  The Docker build workflow always runs on every PR, adding some build
  time.
* **Future Implications:** Downstream blueprints (e.g., a
  cloud-deployment-specific blueprint) can extend these workflows by
  uncommenting the publish step or adding registry push steps with
  minimal changes. See ADR-006 for Docker conventions and ADR-003 for
  Poetry conventions.
