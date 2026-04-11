# example-processing

> Silver layer — validate and transform bronze data into clean entities.

## Purpose

This application demonstrates the **Silver** (processing) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It reads raw bronze data from S3, validates and transforms each record using
Pydantic models, and writes the cleaned output to S3.

**Data flow:** S3 `bronze/{source}/{date}/` → Validate & Transform → S3 `silver/{entity}/{date}/`

## Installation

```bash
cd apps/example-processing
poetry install
```

## Usage

```bash
# Run the processing pipeline
poetry run example-processing process \
    --source api-source \
    --entity users \
    --date 2026-01-15
```

## Customization

1. Replace `read_from_s3()` in `app/main.py` with real `boto3` S3 reads
2. Implement domain-specific logic in `transform_record()`
3. Update `SilverEntity` in `libs/example-data/` with your validated fields
4. Replace `write_to_s3()` with real `boto3` calls

## Development

```bash
cd apps/example-processing
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
