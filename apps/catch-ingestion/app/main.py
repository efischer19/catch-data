"""Bronze layer ingestion pipeline for raw MLB schedule data."""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

import click
import requests
from botocore.exceptions import ClientError
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


def default_target_date() -> date:
    """Return the default ingestion date (yesterday)."""
    return date.today() - timedelta(days=1)


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


def parse_target_date(raw_value: str | None) -> date:
    """Parse an optional CLI date override, defaulting to yesterday."""
    if raw_value is None:
        return default_target_date()

    try:
        return date.fromisoformat(raw_value)
    except ValueError as error:
        raise click.BadParameter("Use YYYY-MM-DD format for --date") from error


def read_json_from_s3(s3_client: Any, bucket: str, key: str) -> dict[str, Any]:
    """Read and decode a JSON object from S3."""
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read().decode("utf-8")
    return json.loads(body)


def s3_key_exists(s3_client: Any, bucket: str, key: str) -> bool:
    """Return whether an S3 object already exists."""
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise

    return True


def upload_json_to_s3(
    s3_client: Any,
    bucket: str,
    key: str,
    payload: dict[str, Any],
) -> int:
    """Upload a raw JSON payload to S3."""
    body = json.dumps(payload).encode("utf-8")
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    return len(body)


def is_final_game(schedule_game: dict[str, Any]) -> bool:
    """Return whether a raw schedule game payload is final."""
    status = schedule_game.get("status")
    if not isinstance(status, dict):
        return False

    return (
        status.get("abstractGameState") == "Final"
        or status.get("detailedState") == "Final"
    )


def completed_game_pks_for_date(
    schedule_payload: dict[str, Any],
    target_date: date,
) -> list[int]:
    """Return completed game IDs for the requested official date."""
    game_pks: list[int] = []

    for schedule_date in schedule_payload.get("dates", []):
        if not isinstance(schedule_date, dict):
            continue
        if schedule_date.get("date") != target_date.isoformat():
            continue

        for schedule_game in schedule_date.get("games", []):
            if not isinstance(schedule_game, dict) or not is_final_game(schedule_game):
                continue

            game_pk = schedule_game.get("gamePk")
            if isinstance(game_pk, int):
                game_pks.append(game_pk)

    return game_pks


def ingest_completed_games(
    s3_client: Any,
    mlb_client: MlbStatsClient,
    bucket: str,
    target_date: date,
) -> dict[str, Any]:
    """Upload boxscore and content JSON for completed games on one date."""
    schedule_key = CatchPaths.bronze_schedule_key(target_date.year)
    schedule_payload = read_json_from_s3(s3_client, bucket, schedule_key)
    game_pks = completed_game_pks_for_date(schedule_payload, target_date)

    game_plan: list[tuple[int, bool, bool]] = []
    for game_pk in game_pks:
        boxscore_key = CatchPaths.bronze_boxscore_key(game_pk)
        content_key = CatchPaths.bronze_content_key(game_pk)
        game_plan.append(
            (
                game_pk,
                s3_key_exists(s3_client, bucket, boxscore_key),
                s3_key_exists(s3_client, bucket, content_key),
            ),
        )

    games_skipped = sum(
        1
        for _, boxscore_exists, content_exists in game_plan
        if boxscore_exists and content_exists
    )
    games_to_process = len(game_plan) - games_skipped
    boxscores_uploaded = 0
    contents_uploaded = 0
    games_uploaded = 0

    logger.info(
        "Completed games for %s total_games=%d games_to_process=%d games_skipped=%d",
        target_date.isoformat(),
        len(game_pks),
        games_to_process,
        games_skipped,
    )

    for game_pk, boxscore_exists, content_exists in game_plan:
        if boxscore_exists and content_exists:
            logger.info("Skipping game_pk=%s; Bronze objects already exist", game_pk)
            continue

        uploaded_for_game = False

        if not boxscore_exists:
            boxscore_key = CatchPaths.bronze_boxscore_key(game_pk)
            try:
                boxscore_payload = mlb_client.get_boxscore(game_pk)
                file_size = upload_json_to_s3(
                    s3_client,
                    bucket,
                    boxscore_key,
                    boxscore_payload,
                )
            except requests.RequestException:
                logger.exception("Failed to ingest boxscore for game_pk=%s", game_pk)
            else:
                boxscores_uploaded += 1
                uploaded_for_game = True
                logger.info(
                    "Uploaded boxscore to s3://%s/%s file_size=%d game_pk=%s",
                    bucket,
                    boxscore_key,
                    file_size,
                    game_pk,
                )

        if not content_exists:
            content_key = CatchPaths.bronze_content_key(game_pk)
            try:
                content_payload = mlb_client.get_content(game_pk)
                file_size = upload_json_to_s3(
                    s3_client,
                    bucket,
                    content_key,
                    content_payload,
                )
            except requests.HTTPError as error:
                response = error.response
                if response is not None and response.status_code == 404:
                    logger.warning(
                        "Content not found for game_pk=%s; skipping content upload",
                        game_pk,
                    )
                else:
                    logger.exception("Failed to ingest content for game_pk=%s", game_pk)
            except requests.RequestException:
                logger.exception("Failed to ingest content for game_pk=%s", game_pk)
            else:
                contents_uploaded += 1
                uploaded_for_game = True
                logger.info(
                    "Uploaded content to s3://%s/%s file_size=%d game_pk=%s",
                    bucket,
                    content_key,
                    file_size,
                    game_pk,
                )

        if uploaded_for_game:
            games_uploaded += 1

    logger.info(
        (
            "Finished ingest-games target_date=%s total_games=%d "
            "games_to_process=%d games_skipped=%d games_uploaded=%d"
        ),
        target_date.isoformat(),
        len(game_pks),
        games_to_process,
        games_skipped,
        games_uploaded,
    )

    return {
        "bucket": bucket,
        "date": target_date.isoformat(),
        "games_found": len(game_pks),
        "games_skipped": games_skipped,
        "games_to_process": games_to_process,
        "games_uploaded": games_uploaded,
        "boxscores_uploaded": boxscores_uploaded,
        "contents_uploaded": contents_uploaded,
        "schedule_key": schedule_key,
    }


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


@cli.command("ingest-games")
@click.option(
    "--date",
    "target_date_value",
    default=None,
    help="Official game date to ingest (YYYY-MM-DD). Defaults to yesterday.",
)
@click.option(
    "--bucket",
    default=None,
    envvar="S3_BUCKET_NAME",
    help="Bronze S3 bucket for raw game uploads.",
)
def ingest_games(target_date_value: str | None, bucket: str | None):
    """Fetch completed-game boxscore/content JSON and upload to Bronze S3."""
    if not bucket:
        raise click.ClickException("Provide --bucket or set S3_BUCKET_NAME")

    target_date = parse_target_date(target_date_value)

    try:
        summary = ingest_completed_games(
            create_s3_client(),
            create_mlb_client(),
            bucket,
            target_date,
        )
    except ClientError as error:
        logger.exception(
            "Failed to read Bronze schedule for date=%s",
            target_date.isoformat(),
        )
        raise click.ClickException(
            f"Failed to read Bronze schedule for date={target_date.isoformat()}"
        ) from error

    click.echo(json.dumps(summary))


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
