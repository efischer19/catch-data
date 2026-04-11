# example-analytics

> Gold layer — aggregate silver data into business-ready metrics.

## Purpose

This application demonstrates the **Gold** (analytics) stage of the
[medallion architecture](../../meta/adr/ADR-018-medallion_architecture.md).
It reads validated silver data from S3, computes business metrics and
aggregations, and writes the results to S3 for consumption.

**Data flow:** S3 `silver/{entity}/{date}/` → Aggregate → S3 `gold/served/{metric_name}/`

## Installation

```bash
cd apps/example-analytics
poetry install
```

## Usage

```bash
# Run the analytics pipeline
poetry run example-analytics aggregate \
    --entity users \
    --metric-name daily-active-users \
    --date 2026-01-15
```

## Customization

1. Replace `read_from_s3()` in `app/main.py` with real `boto3` S3 reads
2. Implement domain-specific aggregation logic in `compute_metrics()`
3. Update `GoldMetric` in `libs/example-data/` with your business metric fields
4. Replace `write_to_s3()` with real `boto3` calls

## Development

```bash
cd apps/example-analytics
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
