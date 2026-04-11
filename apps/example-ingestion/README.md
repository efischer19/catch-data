# example-ingestion

> Bronze layer — ingest raw data from external sources into S3.

## Purpose

This application demonstrates the **Bronze** (ingestion) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It fetches raw data from an external source and writes it to S3 with minimal
transformation.

**Data flow:** External Source → Validate (minimal) → S3 `bronze/{source}/{date}/`

## Installation

```bash
cd apps/example-ingestion
poetry install
```

## Usage

```bash
# Run the ingestion pipeline
poetry run example-ingestion ingest --source api-source --date 2026-01-15
```

## Customization

1. Replace `fetch_from_source()` in `app/main.py` with your real data source
2. Update `BronzeRecord` in `libs/example-data/` with your raw data fields
3. Replace `write_to_s3()` with real `boto3` calls

## Development

```bash
cd apps/example-ingestion
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```

## Dependencies

* **[example-data](../../libs/example-data/)** — Shared data models and
  S3 path conventions (path dependency)
* **[Click](https://click.palletsprojects.com/)** — CLI framework
  (see [ADR-011](../../meta/adr/ADR-011-use_click.md))
