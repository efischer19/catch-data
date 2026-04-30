# catch-analytics

> Gold layer — transform the Silver master schedule into frontend-ready JSON.

## Purpose

This application implements the **Gold** (analytics) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It reads the validated Silver master schedule from S3 and writes one
frontend-ready Gold schedule JSON file per MLB team plus a rolling-window
`gold/upcoming_games.json` view for the frontend "Today's Slate". After
writing all Gold files, the Lambda reads each one back and validates it
against the Gold Pydantic models before optionally invalidating CloudFront.

**Data flow:** S3 `silver/master_schedule_{year}.json` → Transform →
`gold/team_{team_id}.json` and `gold/upcoming_games.json`

## Installation

```bash
cd apps/catch-analytics
poetry install
```

## Usage

```bash
# Build all 30 team schedule files and the upcoming-games view for a season
poetry run catch-analytics aggregate \
    --year 2026 \
    --bucket catch-data-data-dev
```

Set `CLOUDFRONT_DISTRIBUTION_ID` to trigger a cache invalidation for the
written Gold paths after validation succeeds.

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
