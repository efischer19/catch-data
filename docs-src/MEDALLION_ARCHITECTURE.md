# Medallion Architecture

This project includes a **medallion architecture** example that demonstrates
a Bronze/Silver/Gold data pipeline pattern using S3 and AWS Lambda.

!!! info "This is scaffolding, not a working pipeline"
    The example apps contain placeholder logic with comments showing where
    to add real data processing. Replace the `TODO` markers with your
    domain-specific code.

## Overview

The medallion architecture organizes data pipelines into three progressive
layers of data quality:

```text
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    Bronze     │     │      Silver      │     │       Gold       │
│  (Ingestion)  │ ──► │  (Processing)    │ ──► │   (Analytics)    │
│              │     │                  │     │                  │
│ Raw data from│     │ Validated &      │     │ Aggregated       │
│ external     │     │ transformed      │     │ business-ready   │
│ sources      │     │ entities         │     │ metrics          │
└──────────────┘     └──────────────────┘     └──────────────────┘
```

| Layer | Application | S3 Prefix | Description |
| :--- | :--- | :--- | :--- |
| **Bronze** | `apps/example-ingestion/` | `bronze/{source}/{date}/` | Raw data with minimal validation |
| **Silver** | `apps/example-processing/` | `silver/{entity}/{date}/` | Cleaned and validated entities |
| **Gold** | `apps/example-analytics/` | `gold/served/{metric_name}/` | Business-ready aggregations |

## S3 Key Conventions

All data is stored in a single S3 bucket with key prefixes to separate
the layers:

```text
s3://{{S3_BUCKET_NAME}}/
├── bronze/{source}/{YYYY-MM-DD}/       # Raw ingested data
├── silver/{entity}/{YYYY-MM-DD}/       # Cleaned & validated data
└── gold/served/{metric_name}/          # Business-ready aggregations
```

The `MedallionPaths` utility in `libs/example-data/` generates these
prefixes consistently:

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

## Shared Data Models

The `libs/example-data/` library provides Pydantic model skeletons for
each layer:

* **`BronzeRecord`** — Raw ingested record with source metadata
* **`SilverEntity`** — Cleaned, validated entity with strict types
* **`GoldMetric`** — Aggregated business metric with dimensions

These models enforce data contracts between pipeline stages. Customize
them with your domain-specific fields.

## How to Customize

### 1. Define Your Data Models

Edit the models in `libs/example-data/example_data/models.py` to match
your domain:

```python
class SilverEntity(BaseModel):
    entity_id: str
    email: EmailStr              # Add validated fields
    category: Literal["A", "B"]  # Add constrained types
    score: float = Field(ge=0, le=100)
```

### 2. Implement Data Source Logic

In `apps/example-ingestion/app/main.py`, replace `fetch_from_source()`
with your real data source:

```python
def fetch_from_source() -> list[dict]:
    response = requests.get("https://api.example.com/data")
    response.raise_for_status()
    return response.json()["results"]
```

### 3. Add S3 Integration

Replace the placeholder `read_from_s3()` and `write_to_s3()` functions
with real `boto3` calls. See the docstrings in each `app/main.py` for
example implementations.

### 4. Configure Scheduling

Edit the workflow stubs in `.github/workflows/pipeline-*.yml` to enable
scheduled runs. Uncomment the cron expressions and adjust the timing to
match your data source update frequency.

## Architecture Decision

See `meta/adr/ADR-018-medallion_architecture.md` in the repository root
for the full rationale and design considerations.
