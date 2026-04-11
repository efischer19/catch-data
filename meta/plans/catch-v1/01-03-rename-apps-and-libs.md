# feat: Rename example apps and libs to catch-specific names

## What do you want to build?

Rename the template's example applications and libraries to project-specific
names that reflect the Catch data pipeline. This includes renaming directories,
Python packages, pyproject.toml metadata, Click entry points, Dockerfiles, and
all internal import references.

The mapping is:

| Template Name | Catch Name | Purpose |
| --- | --- | --- |
| `apps/example-ingestion` | `apps/catch-ingestion` | Bronze layer — MLB API ingestion |
| `apps/example-processing` | `apps/catch-processing` | Silver layer — data cleaning/joining |
| `apps/example-analytics` | `apps/catch-analytics` | Gold layer — UI-ready JSON generation |
| `libs/example-data` | `libs/catch-models` | Shared Pydantic models and S3 paths |
| `apps/example-app` | _(remove)_ | Not needed — no generic app in Catch |
| `libs/example-lib` | _(remove)_ | Not needed — single shared lib is sufficient |

## Acceptance Criteria

- [ ] `apps/catch-ingestion/` exists with `app/` package, `tests/`, `Dockerfile`, `pyproject.toml`, and `poetry.lock`
- [ ] `apps/catch-processing/` exists with the same structure
- [ ] `apps/catch-analytics/` exists with the same structure
- [ ] `libs/catch-models/` exists with `catch_models/` Python package, `tests/`, `pyproject.toml`, and `poetry.lock`
- [ ] All pyproject.toml files reference the new package names and path dependencies (e.g., `catch-models = { path = "../../libs/catch-models", develop = true }`)
- [ ] Click entry points in pyproject.toml use catch-specific names (e.g., `catch-ingestion = "app.main:cli"`)
- [ ] `apps/example-app/` and `libs/example-lib/` are removed
- [ ] `apps/example-ingestion/`, `apps/example-processing/`, `apps/example-analytics/`, and `libs/example-data/` are removed
- [ ] All internal imports compile and `poetry install` succeeds in each project
- [ ] `poetry run pytest` passes in each project (existing template tests adapted)

## Implementation Notes

Follow the existing naming conventions from ADR-007 (monorepo structure):

- Directory names: kebab-case (`catch-ingestion`)
- Python packages: snake_case (`catch_models`)
- Entry points: kebab-case matching directory name

The `apps/example-app/` and `libs/example-lib/` directories are generic
template examples with no pipeline-specific logic. Remove them entirely to
reduce confusion.

Preserve the Dockerfile multi-stage pattern from the templates — just update
the `COPY` paths and package names. Keep the Lambda handler structure intact.

Run `poetry lock` in each project after updating `pyproject.toml` to regenerate
lock files. Verify with `poetry install && poetry run pytest` in each directory.
