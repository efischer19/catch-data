# catch-ingestion

> Bronze layer — ingest raw data from external sources into S3.

## Purpose

This application implements the **Bronze** (ingestion) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It fetches the current MLB season schedule from the MLB Stats API and writes
the raw JSON response to S3 with minimal transformation. It also ingests raw
boxscore and content JSON for recently completed games using the Bronze
schedule file as the source of truth.

**Data flow:** MLB Stats API → Preserve raw JSON → S3 Bronze objects

## Installation

```bash
cd apps/catch-ingestion
poetry install
```

## Usage

```bash
# Ingest the current season schedule
poetry run catch-ingestion ingest-schedule --bucket catch-data-data-dev

# Ingest a specific season schedule
poetry run catch-ingestion ingest-schedule \
    --year 2026 \
    --bucket catch-data-data-dev

# Ingest yesterday's completed games using the Bronze schedule file
poetry run catch-ingestion ingest-games --bucket catch-data-data-dev

# Re-run completed-game ingestion for a specific date
poetry run catch-ingestion ingest-games \
    --date 2025-06-15 \
    --bucket catch-data-data-dev
```

## Development

```bash
cd apps/catch-ingestion
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
* **[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)** —
  AWS SDK used for Bronze S3 uploads
