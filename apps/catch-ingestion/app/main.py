"""Bronze layer ingestion pipeline for raw MLB schedule data."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import click
import requests
from catch_models import CatchPaths

from app.mlb_client import MlbStatsClient

logger = logging.getLogger(__name__)


def create_s3_client():
    """Create an S3 client lazily so tests can monkeypatch it easily."""
    import boto3

    return boto3.client("s3")


def create_mlb_client() -> MlbStatsClient:
    """Create the MLB Stats API client."""
    return MlbStatsClient()


def current_year() -> int:
    """Return the current calendar year."""
    return date.today().year


def schedule_game_count(schedule_payload: dict[str, Any]) -> int:
    """Count games in a raw schedule payload."""
    total_games = schedule_payload.get("totalGames")
    if isinstance(total_games, int):
        return total_games

    return sum(
        len(schedule_date.get("games", []))
        for schedule_date in schedule_payload.get("dates", [])
        if isinstance(schedule_date, dict)
    )


def upload_schedule_to_s3(
    s3_client: Any,
    bucket: str,
    year: int,
    schedule_payload: dict[str, Any],
) -> tuple[str, int, int]:
    """Upload a season schedule JSON payload to the Bronze S3 layer."""
    key = CatchPaths.bronze_schedule_key(year)
    body = json.dumps(schedule_payload).encode("utf-8")
    game_count = schedule_game_count(schedule_payload)

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )

    return key, len(body), game_count


@click.group()
def cli():
    """Bronze layer ingestion pipeline CLI."""
    logging.basicConfig(level=logging.INFO)


@cli.command("ingest-schedule")
@click.option(
    "--year",
    type=int,
    default=current_year,
    show_default="current year",
    help="Season year to ingest.",
)
@click.option(
    "--bucket",
    default=None,
    envvar="S3_BUCKET_NAME",
    help="Bronze S3 bucket for raw schedule uploads.",
)
def ingest_schedule(year: int, bucket: str | None):
    """Fetch a full MLB season schedule and upload the raw JSON to S3."""
    if not bucket:
        raise click.ClickException("Provide --bucket or set S3_BUCKET_NAME")

    try:
        schedule_payload = create_mlb_client().get_schedule(year)
    except requests.RequestException as error:
        logger.exception("Failed to fetch schedule for year=%s", year)
        raise click.ClickException(
            f"Failed to fetch schedule for year={year}"
        ) from error

    output_key, file_size, game_count = upload_schedule_to_s3(
        create_s3_client(),
        bucket,
        year,
        schedule_payload,
    )
    logger.info(
        "Uploaded schedule to s3://%s/%s file_size=%d games=%d",
        bucket,
        output_key,
        file_size,
        game_count,
    )

    click.echo(
        json.dumps(
            {
                "bucket": bucket,
                "file_size": file_size,
                "games_found": game_count,
                "output_key": output_key,
                "year": year,
            },
        ),
    )


if __name__ == "__main__":
    cli()
