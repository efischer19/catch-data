# catch-analytics

> Gold layer — transform the Silver master schedule into frontend-ready team JSON.

## Purpose

This application implements the **Gold** (analytics) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It reads the validated Silver master schedule from S3 and writes one
frontend-ready Gold schedule JSON file per MLB team.

**Data flow:** S3 `silver/master_schedule_{year}.json` → Transform → `gold/team_{team_id}.json`

## Installation

```bash
cd apps/catch-analytics
poetry install
```

## Usage

```bash
# Build all 30 team schedule files for a season
poetry run catch-analytics aggregate \
    --year 2026 \
    --bucket catch-data-data-dev
```

## Development

```bash
cd apps/catch-analytics
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```

## Dependencies

* **[catch-models](../../libs/catch-models/)** — Shared data models and
  S3 path conventions (path dependency)
* **[Click](https://click.palletsprojects.com/)** — CLI framework
  (see [ADR-011](../../meta/adr/ADR-011-use_click.md))
