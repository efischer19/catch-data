"""Gold layer analytics pipeline — aggregate data into business metrics.

This module demonstrates the Gold (analytics) stage of the medallion
architecture. It reads validated silver data from S3, computes
aggregations and business metrics, and writes the results to the
``gold/served/{metric_name}/`` prefix in S3.

Data flow::

    S3 silver/{entity}/{date}/  ──►  Aggregate  ──►  S3 gold/served/{metric_name}/

See ADR-018 (Medallion Architecture) for pattern context.

Customize this module:
    1. Replace the placeholder ``read_from_s3`` with real ``boto3`` calls
       to read silver data.
    2. Implement your aggregation logic in ``compute_metrics``.
    3. Update ``GoldMetric`` in ``libs/example-data`` with your business
       metric fields.
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
    """Read silver records from S3.

    Parameters
    ----------
    s3_key_prefix : str
        The S3 key prefix for silver data
        (e.g., ``"silver/users/2026-01-15/"``).

    Returns
    -------
    list[dict]
        Validated silver records read from S3.

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
        {"entity_id": "1", "name": "example-a"},
        {"entity_id": "2", "name": "example-b"},
        {"entity_id": "3", "name": "example-a"},
    ]


# ---------------------------------------------------------------------------
# Aggregation logic — replace with your domain-specific computations
# ---------------------------------------------------------------------------
def compute_metrics(records: list[dict]) -> list[dict]:
    """Compute business metrics from silver records.

    Parameters
    ----------
    records : list[dict]
        Validated silver records.

    Returns
    -------
    list[dict]
        Computed metrics ready for the gold layer.

    Customize this function:
        - Implement grouping, counting, averaging, or other aggregations.
        - Add dimensions for slicing (region, category, etc.).
        - Return one dict per metric/dimension combination.
    """
    # TODO: Replace with real aggregation logic.
    # Example: count records by name
    counts: dict[str, int] = {}
    for record in records:
        name = record.get("name", "unknown")
        counts[name] = counts.get(name, 0) + 1

    return [
        {
            "metric_name": "record-count-by-name",
            "value": float(count),
            "dimensions": {"name": name},
        }
        for name, count in counts.items()
    ]


# ---------------------------------------------------------------------------
# S3 writer — replace with real boto3 calls
# ---------------------------------------------------------------------------
def write_to_s3(records: list[dict], s3_key_prefix: str) -> int:
    """Write gold metrics to S3 as newline-delimited JSON.

    Parameters
    ----------
    records : list[dict]
        Computed metrics to persist.
    s3_key_prefix : str
        The S3 key prefix (e.g., ``"gold/served/daily-metrics/"``).

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
    """Gold layer analytics pipeline CLI."""


@cli.command()
@click.option("--entity", default="entities", help="Silver entity type to aggregate.")
@click.option(
    "--metric-name", default="summary-metrics", help="Name of the output metric."
)
@click.option(
    "--date",
    "processing_date",
    default=None,
    help="Processing date (YYYY-MM-DD). Defaults to today.",
)
def aggregate(entity: str, metric_name: str, processing_date: str | None):
    """Aggregate silver data into gold business metrics.

    Reads validated entities from the silver prefix, computes metrics,
    validates them with the GoldMetric model, and writes results to the
    gold served prefix.
    """
    from datetime import date as date_type

    from example_data import GoldMetric, MedallionPaths

    processing = (
        date_type.fromisoformat(processing_date)
        if processing_date
        else date_type.today()
    )

    paths = MedallionPaths("{{S3_BUCKET_NAME}}")
    silver_prefix = paths.silver(entity, processing)
    gold_prefix = paths.gold(metric_name)

    click.echo(f"Reading silver data from {silver_prefix}")

    silver_records = read_from_s3(silver_prefix)
    click.echo(f"Read {len(silver_records)} silver records")

    raw_metrics = compute_metrics(silver_records)

    gold_records = []
    for raw in raw_metrics:
        validated = GoldMetric(**raw)
        gold_records.append(json.loads(validated.model_dump_json()))

    click.echo(f"Computed {len(gold_records)} gold metrics")

    count = write_to_s3(gold_records, gold_prefix)
    click.echo(f"Wrote {count} gold metrics to {gold_prefix}")


if __name__ == "__main__":
    cli()
