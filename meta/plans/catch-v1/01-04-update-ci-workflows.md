# feat: Update CI/CD workflows for catch-specific apps and libs

## What do you want to build?

Update all GitHub Actions workflows to reference the renamed catch-specific
applications and libraries instead of the template `example-*` names. This
includes the CI matrix, pipeline workflows, Docker build workflows, and any
composite actions.

## Acceptance Criteria

- [ ] `.github/workflows/ci.yml` matrix includes `apps/catch-ingestion`, `apps/catch-processing`, `apps/catch-analytics`, and `libs/catch-models` (and no `example-*` entries)
- [ ] `.github/workflows/pipeline-ingestion.yml` references `apps/catch-ingestion` and uses `catch-ingestion` as the CLI entry point
- [ ] `.github/workflows/pipeline-processing.yml` references `apps/catch-processing` and uses `catch-processing` as the CLI entry point
- [ ] `.github/workflows/pipeline-analytics.yml` references `apps/catch-analytics` and uses `catch-analytics` as the CLI entry point
- [ ] `.github/workflows/build-docker.yml` and `reusable-build-push.yml` reference updated paths
- [ ] All workflow files pass YAML lint validation
- [ ] A manual `workflow_dispatch` of the CI workflow succeeds on the updated branch

## Implementation Notes

The pipeline workflows (ingestion, processing, analytics) have schedule triggers
commented out by default. Keep them commented — they will be enabled once the
actual pipeline logic is implemented in later epics.

Update the `working-directory` and `poetry run` commands to match the new
entry-point names defined in pyproject.toml (e.g., `catch-ingestion ingest`
instead of `example-ingestion ingest`).

Also update `.github/workflows/deploy.yml` if it references example app names,
and the documentation workflow if it builds API docs for specific packages.

Reference ADR-014 (CI/CD Strategy) for the expected workflow structure.
