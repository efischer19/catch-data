"""Bronze layer ingestion pipeline — fetch and store raw data.

This module demonstrates the Bronze (ingestion) stage of the medallion
architecture. It reads data from an external source and writes the raw
payload to the ``bronze/{source}/{date}/`` prefix in S3.

Data flow::

    External Source  ──►  Validate (minimal)  ──►  S3 bronze/{source}/{date}/

See ADR-018 (Medallion Architecture) for pattern context.

Customize this module:
    1. Replace the placeholder ``fetch_from_source`` with your real data
       source (API call, database query, file download, etc.).
    2. Adjust the BronzeRecord fields in ``libs/example-data`` to match
       your raw data schema.
    3. Replace the ``write_to_s3`` placeholder with real ``boto3`` calls.
"""

import json
import logging

import click

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data source — replace with your real data fetching logic
# ---------------------------------------------------------------------------
def fetch_from_source() -> list[dict]:
    """Fetch raw data from an external source.

    Returns
    -------
    list[dict]
        A list of raw records from the external source.

    Example implementation::

        import boto3
        import requests

        def fetch_from_source() -> list[dict]:
            response = requests.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()["results"]
    """
    # TODO: Replace with real data source logic.
    logger.info("Fetching data from source (placeholder)")
    return [
        {"id": "1", "value": "example-raw-record"},
    ]


# ---------------------------------------------------------------------------
# S3 writer — replace with real boto3 calls
# ---------------------------------------------------------------------------
def write_to_s3(records: list[dict], s3_key_prefix: str) -> int:
    """Write raw records to S3 as newline-delimited JSON.

    Parameters
    ----------
    records : list[dict]
        Raw records to persist.
    s3_key_prefix : str
        The S3 key prefix (e.g., ``"bronze/api-source/2026-01-15/"``).

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
    """Bronze layer ingestion pipeline CLI."""


@cli.command()
@click.option("--source", default="api-source", help="Name of the data source.")
@click.option(
    "--date",
    "processing_date",
    default=None,
    help="Processing date (YYYY-MM-DD). Defaults to today.",
)
def ingest(source: str, processing_date: str | None):
    """Ingest raw data from an external source into the bronze layer.

    Fetches data from the configured source, wraps each record as a
    BronzeRecord, and writes the results to S3 under the bronze prefix.
    """
    from datetime import date as date_type

    from example_data import BronzeRecord, MedallionPaths

    processing = (
        date_type.fromisoformat(processing_date)
        if processing_date
        else date_type.today()
    )

    click.echo(f"Ingesting from source={source} for date={processing}")

    raw_records = fetch_from_source()

    bronze_records = [
        BronzeRecord(source=source, raw_data=record) for record in raw_records
    ]
    click.echo(f"Validated {len(bronze_records)} bronze records")

    paths = MedallionPaths("{{S3_BUCKET_NAME}}")
    key_prefix = paths.bronze(source, processing)

    serialized = [json.loads(record.model_dump_json()) for record in bronze_records]
    count = write_to_s3(serialized, key_prefix)

    click.echo(f"Wrote {count} records to {key_prefix}")


if __name__ == "__main__":
    cli()
