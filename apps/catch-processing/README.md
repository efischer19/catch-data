# catch-processing

> Silver layer — validate and transform bronze data into clean entities.

## Purpose

This application implements the **Silver** (processing) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It rebuilds a season-level `silver/master_schedule_{year}.json` file by reading
Bronze schedule, boxscore, and content JSON objects from S3, flattening the MLB
API payloads, and validating the joined output with shared Pydantic models.

**Data flow:** S3 `bronze/schedule_{year}.json` + per-game Bronze enrichments →
Validate & Transform → S3 `silver/master_schedule_{year}.json`

## Installation

```bash
cd apps/catch-processing
poetry install
```

## Usage

```bash
# Rebuild the Silver master schedule for one season
poetry run catch-processing process \
    --year 2026 \
    --bucket catch-data-data-dev
```

The deployed entry point is the `lambda_handler` function in `app/main.py`,
which consumes S3 event notifications and derives the target season from the
uploaded Bronze schedule key. Generated Silver files include a
`processing_errors` summary so downstream layers can distinguish excluded games
from successfully validated records. When `SILVER_DLQ_URL` is configured, the
Lambda also publishes failed invocation events to SQS before re-raising.

## Development

```bash
cd apps/catch-processing
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
