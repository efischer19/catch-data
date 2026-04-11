---
title: "ADR-018: Medallion Architecture for Data Pipelines"
status: "Accepted"
date: "2026-04-09"
tags:
  - "data-pipeline"
  - "architecture"
  - "aws"
  - "s3"
---

## Context

* **Problem:** Data pipelines need a clear organizational pattern that
  separates raw ingestion, cleaning/validation, and business-ready
  aggregation into distinct stages. Without a standard structure,
  pipeline code becomes tightly coupled and difficult to extend or debug.
* **Constraints:** The pattern must work with S3 as the primary data
  store (see [ADR-015](ADR-015-aws_cloud_provider.md)) and fit the
  monorepo structure (see [ADR-007](ADR-007-monorepo_apps_structure.md)).
  It should be a scaffolding pattern — easy to understand and customize
  without imposing a specific data processing framework.

## Decision

We will organize data pipelines using the **medallion architecture**
(also known as Bronze/Silver/Gold), with one application per pipeline
stage and a shared library for data models and path conventions.

### Pipeline Stages

| Layer | Stage | Application | S3 Key Prefix | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| Bronze | Ingestion | `apps/example-ingestion/` | `bronze/{source}/{date}/` | Ingest raw data from external sources with minimal transformation |
| Silver | Processing | `apps/example-processing/` | `silver/{entity}/{date}/` | Validate, clean, and transform data using Pydantic models |
| Gold | Analytics | `apps/example-analytics/` | `gold/served/{metric_name}/` | Aggregate data into business-ready metrics and KPIs |

### Shared Data Library

The `libs/example-data/` library provides:

* **Pydantic models** (`BronzeRecord`, `SilverEntity`, `GoldMetric`)
  that define the data contract for each layer.
* **S3 path conventions** (`MedallionPaths`) that generate consistent
  key prefixes for all pipeline stages.

### S3 Key Layout

All pipeline data is stored in a single S3 bucket with key prefixes:

```text
s3://{{S3_BUCKET_NAME}}/
├── bronze/{source}/{YYYY-MM-DD}/       # Raw ingested data
├── silver/{entity}/{YYYY-MM-DD}/       # Cleaned & validated data
└── gold/served/{metric_name}/          # Business-ready aggregations
```

### Key Conventions

* Each pipeline stage is a separate application in `apps/` with its
  own `pyproject.toml`, `Dockerfile`, and test suite.
* All stages share data models via `libs/example-data/` (path dependency).
* Data flows forward through the layers: Bronze → Silver → Gold.
* Each layer reads from the previous layer's S3 prefix and writes to
  its own prefix — no stage modifies upstream data.
* Bronze preserves raw data with minimal validation.
* Silver applies strict Pydantic validation and transformation.
* Gold produces pre-computed aggregations optimized for consumption.

## Considered Options

1. **Medallion Architecture (Chosen):** Three-layer data pipeline with
   Bronze/Silver/Gold separation.
    * *Pros:* Clear separation of concerns. Each layer has a single
      responsibility. Easy to debug — inspect data at any layer.
      Industry-standard pattern (Databricks, dbt, etc.). Maps cleanly
      to the monorepo `apps/` structure.
    * *Cons:* May be more structure than needed for simple pipelines.
      Requires coordination between stages (scheduling, dependencies).
2. **Single Application Pipeline:** One monolithic app handles all
   data processing stages.
    * *Pros:* Simpler deployment. Fewer moving parts.
    * *Cons:* Tightly coupled stages. Harder to test, debug, and scale
      individual stages independently. Violates single-responsibility
      principle.
3. **Lambda-per-Function:** One Lambda function per transformation
   step with Step Functions orchestration.
    * *Pros:* Fine-grained scaling. Native AWS integration.
    * *Cons:* High operational complexity. Vendor lock-in to Step
      Functions. Harder to test locally.

## Consequences

* **Positive:** Pipeline stages are independently deployable, testable,
  and scalable. The shared data library enforces consistent contracts
  between stages. S3 key conventions make data discoverable and
  auditable. The pattern is framework-agnostic — stages can use pandas,
  Polars, Spark, or raw Python as needed.
* **Negative:** Requires scheduling coordination between stages
  (e.g., ingestion must complete before processing starts). Adds
  more directories and files to the monorepo.
* **Future Implications:** Pipeline scheduling is handled by GitHub
  Actions workflow stubs (see `.github/workflows/pipeline-*.yml`).
  As the project grows, consider adding data quality checks between
  layers and implementing dead-letter handling for failed records.
