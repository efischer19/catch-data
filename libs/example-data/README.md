# example-data

> Shared data models and S3 path conventions for the medallion architecture.

## Purpose

This library provides the shared data contracts and path conventions used
across the medallion architecture pipeline stages. It demonstrates:

* Pydantic models for data validation at each pipeline layer
* S3 key path conventions (`bronze/`, `silver/`, `gold/`)
* Path dependency pattern for monorepo consumers
* Testing with pytest

See [ADR-018](../../meta/adr/ADR-018-medallion_architecture.md) for pattern
context.

## Installation

From an application in the monorepo, add a path dependency:

```toml
[tool.poetry.dependencies]
example-data = { path = "../../libs/example-data", develop = true }
```

Then install:

```bash
poetry install
```

## Usage

### Data Models

```python
from example_data import BronzeRecord, SilverEntity, GoldMetric

# Bronze — raw ingested data
record = BronzeRecord(
    source="api-source",
    raw_data={"user_id": "123", "action": "login"},
)

# Silver — cleaned and validated data
entity = SilverEntity(entity_id="usr-123", name="Example User")

# Gold — business-ready metrics
metric = GoldMetric(
    metric_name="daily-active-users",
    value=1234.5,
    dimensions={"region": "us-east-1"},
)
```

### S3 Path Conventions

```python
from datetime import date
from example_data import MedallionPaths

paths = MedallionPaths("my-project-data-dev")

paths.bronze("api-source", date(2026, 1, 15))
# => "bronze/api-source/2026-01-15/"

paths.silver("users", date(2026, 1, 15))
# => "silver/users/2026-01-15/"

paths.gold("daily-active-users")
# => "gold/served/daily-active-users/"
```

## API

### Models

* **`BronzeRecord`** — Raw ingested record with source metadata
* **`SilverEntity`** — Cleaned, validated entity
* **`GoldMetric`** — Aggregated business metric

### Utilities

* **`MedallionPaths(bucket_name)`** — S3 key prefix generator
  * `.bronze(source, date)` → `"bronze/{source}/{date}/"`
  * `.silver(entity, date)` → `"silver/{entity}/{date}/"`
  * `.gold(metric_name)` → `"gold/served/{metric_name}/"`
  * `.s3_uri(key_prefix)` → `"s3://{bucket}/{key_prefix}"`

## Development

```bash
cd libs/example-data
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```

## Dependencies

* **[Pydantic](https://docs.pydantic.dev/)** — Data validation using
  Python type annotations
