"""Bronze layer ingestion pipeline for raw MLB schedule data."""

from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import click
import requests
from botocore.exceptions import ClientError
from catch_models import CatchPaths
from pythonjsonlogger.json import JsonFormatter

from app.mlb_client import MlbStatsClient

logger = logging.getLogger(__name__)
DEFAULT_FAILED_GAMES_FILENAME = "failed_games.json"
DEFAULT_API_CALL_WARNING_THRESHOLD = 100


def create_s3_client():
    """Create an S3 client lazily so tests can monkeypatch it easily."""
    import boto3

    return boto3.client("s3")


def create_mlb_client() -> MlbStatsClient:
    """Create the MLB Stats API client."""
    return MlbStatsClient()


def create_log_formatter(log_format: str) -> logging.Formatter:
    """Create the formatter for the configured log format."""
    if log_format == "json":
        return JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )

    return logging.Formatter("%(levelname)s:%(name)s:%(message)s")


def configure_logging() -> None:
    """Configure application logging for local or JSON structured output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    log_format = os.getenv("LOG_FORMAT", "text").lower()
    formatter = create_log_formatter(log_format)

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        return

    force_json_formatter = log_format == "json"
    for handler in root_logger.handlers:
        if handler.formatter is not None or force_json_formatter:
            handler.setFormatter(formatter)


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


def is_missing_content_error(error: requests.RequestException) -> bool:
    """Return whether a request exception represents a content 404."""
    response = error.response
    return (
        isinstance(error, requests.HTTPError)
        and response is not None
        and response.status_code == 404
    )


def retry_attempt_count(error: BaseException) -> int:
    """Return the number of attempts consumed by a failed API call."""
    attempts = getattr(error, "retry_attempts", 1)
    return attempts if isinstance(attempts, int) and attempts > 0 else 1


def api_call_warning_threshold() -> int:
    """Return the per-run API call warning threshold."""
    raw_value = os.getenv("API_CALL_WARNING_THRESHOLD")
    if raw_value is None:
        return DEFAULT_API_CALL_WARNING_THRESHOLD

    try:
        return max(int(raw_value), 0)
    except ValueError:
        logger.warning(
            "Invalid API_CALL_WARNING_THRESHOLD; using default",
            extra={"configured_value": raw_value},
        )
        return DEFAULT_API_CALL_WARNING_THRESHOLD


def api_call_count(mlb_client: Any) -> int:
    """Return the numeric API call count for a client-like object."""
    value = getattr(mlb_client, "api_call_count", 0)
    return value if isinstance(value, int) and value >= 0 else 0


def failed_games_path() -> Path:
    """Return the local path used to persist failed game primary keys."""
    return Path(os.getenv("FAILED_GAMES_PATH", DEFAULT_FAILED_GAMES_FILENAME))


def write_failed_games_file(failed_game_pks: list[int]) -> str:
    """Persist failed game primary keys for manual retry."""
    path = failed_games_path()
    path.write_text(json.dumps(failed_game_pks), encoding="utf-8")
    return str(path)


def determine_exit_code(summary: dict[str, Any]) -> int:
    """Map the ingestion summary to the documented CLI exit code contract."""
    games_succeeded = summary["games_succeeded"]
    games_failed = summary["games_failed"]

    if games_failed == 0:
        return 0
    if games_succeeded == 0:
        return 2
    return 1


def ingest_completed_games(
    s3_client: Any,
    mlb_client: MlbStatsClient,
    bucket: str,
    target_date: date,
    *,
    dry_run: bool = False,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Upload boxscore and content JSON for completed games on one date."""
    schedule_key = CatchPaths.bronze_schedule_key(target_date.year)
    schedule_payload = read_json_from_s3(s3_client, bucket, schedule_key)
    game_pks = completed_game_pks_for_date(schedule_payload, target_date)
    correlation_id = correlation_id or target_date.isoformat()

    game_ingestion_status: list[tuple[int, bool, bool]] = []
    for game_pk in game_pks:
        boxscore_key = CatchPaths.bronze_boxscore_key(game_pk)
        content_key = CatchPaths.bronze_content_key(game_pk)
        game_ingestion_status.append(
            (
                game_pk,
                s3_key_exists(s3_client, bucket, boxscore_key),
                s3_key_exists(s3_client, bucket, content_key),
            ),
        )

    games_skipped = sum(
        1
        for _, boxscore_exists, content_exists in game_ingestion_status
        if boxscore_exists and content_exists
    )
    games_to_process = len(game_ingestion_status) - games_skipped
    boxscores_uploaded = 0
    contents_uploaded = 0
    games_succeeded = 0
    games_failed = 0
    failed_game_pks: list[int] = []

    logger.info(
        "Completed games discovered",
        extra={
            "bucket": bucket,
            "correlation_id": correlation_id,
            "dry_run": dry_run,
            "games_processed": games_to_process,
            "games_skipped": games_skipped,
            "games_total": len(game_pks),
            "target_date": target_date.isoformat(),
        },
    )

    for game_pk, boxscore_exists, content_exists in game_ingestion_status:
        if boxscore_exists and content_exists:
            logger.info(
                "Skipping already ingested game",
                extra={
                    "correlation_id": correlation_id,
                    "gamePk": game_pk,
                },
            )
            continue

        game_failed = False

        if not boxscore_exists:
            boxscore_key = CatchPaths.bronze_boxscore_key(game_pk)
            if dry_run:
                logger.info(
                    "Dry run would fetch and upload boxscore",
                    extra={
                        "bucket": bucket,
                        "correlation_id": correlation_id,
                        "gamePk": game_pk,
                        "key": boxscore_key,
                    },
                )
            else:
                try:
                    boxscore_payload = mlb_client.get_boxscore(game_pk)
                    file_size = upload_json_to_s3(
                        s3_client,
                        bucket,
                        boxscore_key,
                        boxscore_payload,
                    )
                except requests.RequestException as error:
                    game_failed = True
                    logger.error(
                        "Failed to ingest game",
                        extra={
                            "attempt_count": retry_attempt_count(error),
                            "correlation_id": correlation_id,
                            "error_type": type(error).__name__,
                            "gamePk": game_pk,
                            "resource": "boxscore",
                        },
                        exc_info=error,
                    )
                else:
                    boxscores_uploaded += 1
                    logger.info(
                        "Uploaded boxscore",
                        extra={
                            "bucket": bucket,
                            "correlation_id": correlation_id,
                            "file_size": file_size,
                            "gamePk": game_pk,
                            "key": boxscore_key,
                        },
                    )

        if not content_exists:
            content_key = CatchPaths.bronze_content_key(game_pk)
            if dry_run:
                logger.info(
                    "Dry run would fetch and upload content",
                    extra={
                        "bucket": bucket,
                        "correlation_id": correlation_id,
                        "gamePk": game_pk,
                        "key": content_key,
                    },
                )
            else:
                try:
                    content_payload = mlb_client.get_content(game_pk)
                    file_size = upload_json_to_s3(
                        s3_client,
                        bucket,
                        content_key,
                        content_payload,
                    )
                except requests.RequestException as error:
                    if is_missing_content_error(error):
                        logger.warning(
                            "Content not found for game; skipping content upload",
                            extra={
                                "correlation_id": correlation_id,
                                "gamePk": game_pk,
                            },
                        )
                    else:
                        game_failed = True
                        logger.error(
                            "Failed to ingest game",
                            extra={
                                "attempt_count": retry_attempt_count(error),
                                "correlation_id": correlation_id,
                                "error_type": type(error).__name__,
                                "gamePk": game_pk,
                                "resource": "content",
                            },
                            exc_info=error,
                        )
                else:
                    contents_uploaded += 1
                    logger.info(
                        "Uploaded content",
                        extra={
                            "bucket": bucket,
                            "correlation_id": correlation_id,
                            "file_size": file_size,
                            "gamePk": game_pk,
                            "key": content_key,
                        },
                    )

        if game_failed:
            games_failed += 1
            failed_game_pks.append(game_pk)
        else:
            games_succeeded += 1

    failed_games_file = write_failed_games_file(failed_game_pks)
    threshold = api_call_warning_threshold()
    total_api_calls = api_call_count(mlb_client)
    if total_api_calls > threshold:
        logger.warning(
            "API call threshold exceeded",
            extra={
                "api_call_count": total_api_calls,
                "correlation_id": correlation_id,
                "threshold": threshold,
            },
        )

    logger.info(
        "Ingestion run summary",
        extra={
            "bucket": bucket,
            "correlation_id": correlation_id,
            "dry_run": dry_run,
            "failed_games_file": failed_games_file,
            "games_failed": games_failed,
            "games_processed": games_to_process,
            "games_skipped": games_skipped,
            "games_succeeded": games_succeeded,
            "games_total": len(game_pks),
            "target_date": target_date.isoformat(),
        },
    )

    return {
        "bucket": bucket,
        "correlation_id": correlation_id,
        "date": target_date.isoformat(),
        "dry_run": dry_run,
        "failed_game_pks": failed_game_pks,
        "failed_games_file": failed_games_file,
        "games_failed": games_failed,
        "games_found": len(game_pks),
        "games_processed": games_to_process,
        "games_skipped": games_skipped,
        "games_succeeded": games_succeeded,
        "games_to_process": games_to_process,
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
    configure_logging()


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
@click.option(
    "--dry-run",
    is_flag=True,
    help="Log what would be fetched/uploaded without API calls or S3 writes.",
)
def ingest_games(
    target_date_value: str | None,
    bucket: str | None,
    dry_run: bool,
):
    """Fetch completed-game boxscore/content JSON and upload to Bronze S3."""
    if not bucket:
        raise click.ClickException("Provide --bucket or set S3_BUCKET_NAME")

    target_date = parse_target_date(target_date_value)
    correlation_id = target_date.isoformat()
    mlb_client = create_mlb_client()

    try:
        summary = ingest_completed_games(
            create_s3_client(),
            mlb_client,
            bucket,
            target_date,
            dry_run=dry_run,
            correlation_id=correlation_id,
        )
    except ClientError as error:
        logger.error(
            "Failed to read Bronze schedule",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(error).__name__,
                "target_date": target_date.isoformat(),
            },
            exc_info=error,
        )
        summary = {
            "bucket": bucket,
            "correlation_id": correlation_id,
            "date": target_date.isoformat(),
            "dry_run": dry_run,
            "failed_game_pks": [],
            "failed_games_file": write_failed_games_file([]),
            "games_failed": 0,
            "games_found": 0,
            "games_processed": 0,
            "games_skipped": 0,
            "games_succeeded": 0,
            "games_to_process": 0,
            "boxscores_uploaded": 0,
            "contents_uploaded": 0,
            "schedule_key": CatchPaths.bronze_schedule_key(target_date.year),
        }
        click.echo(json.dumps(summary))
        raise click.exceptions.Exit(2) from error

    click.echo(json.dumps(summary))
    raise click.exceptions.Exit(determine_exit_code(summary))


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
