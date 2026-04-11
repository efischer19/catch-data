"""Silver layer processing pipeline — clean, validate, and transform data.

This module demonstrates the Silver (processing) stage of the medallion
architecture. It reads raw bronze data from S3, validates and transforms
each record using Pydantic models, and writes the cleaned output to the
``silver/{entity}/{date}/`` prefix in S3.

Data flow::

    S3 bronze/{source}/{date}/
        ──►  Validate & Transform
        ──►  S3 silver/{entity}/{date}/

See ADR-018 (Medallion Architecture) for pattern context.

Customize this module:
    1. Replace the placeholder ``read_from_s3`` with real ``boto3`` calls
       to read bronze data.
    2. Implement your transformation logic in ``transform_record``.
    3. Update ``SilverEntity`` in ``libs/example-data`` with your domain
       fields and validation rules.
    4. Replace the ``write_to_s3`` placeholder with real ``boto3`` calls.
"""

import json
import logging

import click

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# S3 reader — replace with real boto3 calls
# ---------------------------------------------------------------------------
def read_from_s3(s3_key_prefix: str) -> list[dict]:
    """Read bronze records from S3.

    Parameters
    ----------
    s3_key_prefix : str
        The S3 key prefix for bronze data
        (e.g., ``"bronze/api-source/2026-01-15/"``).

    Returns
    -------
    list[dict]
        Raw records read from S3.

    Example implementation::

        import boto3
        import os

        def read_from_s3(s3_key_prefix: str) -> list[dict]:
            s3 = boto3.client("s3")
            bucket = os.environ["S3_BUCKET_NAME"]
            response = s3.list_objects_v2(Bucket=bucket, Prefix=s3_key_prefix)
            records = []
            for obj in response.get("Contents", []):
                data = s3.get_object(Bucket=bucket, Key=obj["Key"])
                for line in data["Body"].read().decode().splitlines():
                    records.append(json.loads(line))
            return records
    """
    # TODO: Replace with real S3 read logic using boto3.
    logger.info("Would read from %s (placeholder)", s3_key_prefix)
    return [
        {"source": "api-source", "raw_data": {"id": "1", "value": "example"}},
    ]


# ---------------------------------------------------------------------------
# Transformation logic — replace with your domain-specific transforms
# ---------------------------------------------------------------------------
def transform_record(raw_record: dict) -> dict | None:
    """Transform a bronze record into a silver entity.

    Parameters
    ----------
    raw_record : dict
        A raw bronze record.

    Returns
    -------
    dict or None
        The transformed record, or ``None`` if the record should be
        filtered out (e.g., invalid data).

    Customize this function:
        - Extract and rename fields from the raw data.
        - Apply business rules for cleaning and deduplication.
        - Return ``None`` to skip invalid records.
    """
    # TODO: Replace with real transformation logic.
    raw_data = raw_record.get("raw_data", {})
    entity_id = raw_data.get("id")
    if not entity_id:
        logger.warning("Skipping record without id: %s", raw_record)
        return None

    return {
        "entity_id": entity_id,
        "name": raw_data.get("value", "unknown"),
    }


# ---------------------------------------------------------------------------
# S3 writer — replace with real boto3 calls
# ---------------------------------------------------------------------------
def write_to_s3(records: list[dict], s3_key_prefix: str) -> int:
    """Write silver records to S3 as newline-delimited JSON.

    Parameters
    ----------
    records : list[dict]
        Validated silver records to persist.
    s3_key_prefix : str
        The S3 key prefix (e.g., ``"silver/users/2026-01-15/"``).

    Returns
    -------
    int
        Number of records written.

    Example implementation::

        import boto3
        import os

        def write_to_s3(records: list[dict], s3_key_prefix: str) -> int:
            s3 = boto3.client("s3")
            bucket = os.environ["S3_BUCKET_NAME"]
            key = f"{s3_key_prefix}data.jsonl"
            body = "\\n".join(json.dumps(r) for r in records)
            s3.put_object(Bucket=bucket, Key=key, Body=body)
            return len(records)
    """
    # TODO: Replace with real S3 write logic using boto3.
    logger.info(
        "Would write %d records to %s (placeholder)", len(records), s3_key_prefix
    )
    return len(records)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
@click.group()
def cli():
    """Silver layer processing pipeline CLI."""


@cli.command()
@click.option("--source", default="api-source", help="Bronze source to process.")
@click.option("--entity", default="entities", help="Silver entity type name.")
@click.option(
    "--date",
    "processing_date",
    default=None,
    help="Processing date (YYYY-MM-DD). Defaults to today.",
)
def process(source: str, entity: str, processing_date: str | None):
    """Read bronze data, validate, transform, and write to the silver layer.

    Reads raw data from the bronze prefix, applies transformation and
    Pydantic validation, and writes cleaned entities to the silver prefix.
    """
    from datetime import date as date_type

    from example_data import MedallionPaths, SilverEntity

    processing = (
        date_type.fromisoformat(processing_date)
        if processing_date
        else date_type.today()
    )

    paths = MedallionPaths("{{S3_BUCKET_NAME}}")
    bronze_prefix = paths.bronze(source, processing)
    silver_prefix = paths.silver(entity, processing)

    click.echo(f"Processing bronze data from {bronze_prefix}")

    raw_records = read_from_s3(bronze_prefix)
    click.echo(f"Read {len(raw_records)} bronze records")

    silver_records = []
    skipped = 0
    for raw in raw_records:
        transformed = transform_record(raw)
        if transformed is None:
            skipped += 1
            continue
        validated = SilverEntity(**transformed)
        silver_records.append(json.loads(validated.model_dump_json()))

    click.echo(f"Transformed {len(silver_records)} records, skipped {skipped}")

    count = write_to_s3(silver_records, silver_prefix)
    click.echo(f"Wrote {count} silver records to {silver_prefix}")


if __name__ == "__main__":
    cli()
