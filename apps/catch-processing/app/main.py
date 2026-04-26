"""Silver layer Lambda for cleaning and joining Bronze MLB game data."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote_plus

import click
from catch_models import (
    BoxscoreResponse,
    CatchPaths,
    ContentResponse,
    DataCompleteness,
    ScheduleGame,
    ScheduleResponse,
    SilverGame,
    SilverMasterSchedule,
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

_SCHEDULE_KEY_RE = re.compile(r"(^|/)bronze/schedule_(?P<year>\d{4})\.json$")
_MISSING_OBJECT_ERROR_CODES = {"404", "NoSuchKey", "NotFound"}
_TEAM_ABBREVIATIONS_BY_ID = {
    108: "LAA",
    109: "ARI",
    110: "BAL",
    111: "BOS",
    112: "CHC",
    113: "CIN",
    114: "CLE",
    115: "COL",
    116: "DET",
    117: "HOU",
    118: "KC",
    119: "LAD",
    120: "WSH",
    121: "NYM",
    133: "ATH",
    134: "PIT",
    135: "SD",
    136: "SEA",
    137: "SF",
    138: "STL",
    139: "TB",
    140: "TEX",
    141: "TOR",
    142: "MIN",
    143: "PHI",
    144: "ATL",
    145: "CWS",
    146: "MIA",
    147: "NYY",
    158: "MIL",
    198: "AL",
    199: "NL",
}
_TEAM_ABBREVIATIONS_BY_NAME = {
    "Anaheim Angels": "LAA",
    "Arizona Diamondbacks": "ARI",
    "Athletics": "ATH",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Cleveland Indians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "National League All-Stars": "NL",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD",
    "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH",
    "American League All-Stars": "AL",
}


def create_s3_client():
    """Create an S3 client lazily so tests do not require boto3 installed."""
    import boto3

    return boto3.client("s3")


def write_to_s3(records: list[dict], s3_key_prefix: str) -> int:
    """Retain the template-style S3 writer used by the legacy placeholder test."""
    logger.info(
        "Would write %d records to %s (placeholder)", len(records), s3_key_prefix
    )
    return len(records)


def current_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


def extract_year_from_s3_event(event: dict[str, Any]) -> int:
    """Extract the season year from the uploaded schedule object key."""
    record = _first_s3_record(event)
    key = unquote_plus(record["s3"]["object"]["key"])
    match = _SCHEDULE_KEY_RE.search(key)
    if match is None:
        raise ValueError(f"Unsupported S3 event key for schedule rebuild: {key}")
    return int(match.group("year"))


def _first_s3_record(event: dict[str, Any]) -> dict[str, Any]:
    records = event.get("Records", [])
    if not records:
        raise ValueError("S3 event must include at least one record")
    return records[0]


def _bucket_name_from_event(event: dict[str, Any]) -> str:
    record = _first_s3_record(event)
    return record["s3"]["bucket"]["name"]


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _parse_source_updated_at(
    schedule_game: ScheduleGame,
    boxscore: BoxscoreResponse | None,
) -> datetime:
    if (
        boxscore is not None
        and boxscore.metaData is not None
        and boxscore.metaData.timeStamp is not None
    ):
        try:
            return datetime.strptime(
                boxscore.metaData.timeStamp,
                "%Y%m%d_%H%M%S",
            ).replace(
                tzinfo=UTC,
            )
        except ValueError as error:
            raise ValueError(
                "Unsupported boxscore metadata timestamp "
                f"{boxscore.metaData.timeStamp!r}; expected YYYYMMDD_HHMMSS"
            ) from error
    if boxscore is not None and boxscore.gameData.datetime.dateTime is not None:
        return _parse_timestamp(boxscore.gameData.datetime.dateTime)
    return _parse_timestamp(schedule_game.gameDate)


def _team_abbreviation(
    team_id: int,
    team_name: str,
    boxscore_abbreviation: str | None,
) -> str:
    if boxscore_abbreviation:
        return boxscore_abbreviation
    if team_id in _TEAM_ABBREVIATIONS_BY_ID:
        return _TEAM_ABBREVIATIONS_BY_ID[team_id]
    if team_name in _TEAM_ABBREVIATIONS_BY_NAME:
        return _TEAM_ABBREVIATIONS_BY_NAME[team_name]
    logger.error(
        "Missing team abbreviation mapping for id=%s name=%s",
        team_id,
        team_name,
    )
    raise ValueError(
        f"Unsupported team abbreviation mapping for id={team_id} name={team_name}"
    )


def _playback_resolution(playback: Any) -> int:
    width = int(playback.width) if getattr(playback, "width", None) else 0
    height = int(playback.height) if getattr(playback, "height", None) else 0
    return width * height


def _best_playback_url(playbacks: list[Any]) -> str | None:
    playable = [
        playback
        for playback in playbacks
        if hasattr(playback, "url") and playback.url.endswith(".mp4")
    ]
    if not playable:
        return None
    playable.sort(
        key=lambda playback: (
            playback.name == "mp4Avc",
            _playback_resolution(playback),
        ),
        reverse=True,
    )
    return playable[0].url


def _is_condensed_candidate(
    item_type: str | None,
    title: str | None,
    description: str | None,
    container_title: str | None = None,
) -> bool:
    if item_type == "condensedGame":
        return True

    combined_text = " ".join(
        value.lower() for value in (container_title, title, description) if value
    )
    return "condensed" in combined_text or "extended highlights" in combined_text


def extract_condensed_game_url(content: ContentResponse | None) -> str | None:
    """Extract the preferred condensed-game MP4 URL from MLB content data."""
    if content is None:
        return None

    candidate_playbacks = []

    highlight_items = []
    if content.highlights and content.highlights.highlights:
        highlight_items = content.highlights.highlights.items or []
    for item in highlight_items:
        if _is_condensed_candidate(item.type, item.title, item.description):
            candidate_playbacks.extend(item.playbacks)

    epg_entries = []
    if content.media and content.media.epg:
        epg_entries = content.media.epg
    for entry in epg_entries:
        for item in entry.items:
            if _is_condensed_candidate(
                item.type,
                item.title,
                item.description,
                entry.title,
            ):
                candidate_playbacks.extend(item.playbacks or [])

    return _best_playback_url(candidate_playbacks)


def _is_missing_object_error(error: Exception) -> bool:
    response = getattr(error, "response", None)
    if not isinstance(response, dict):
        return False
    code = str(response.get("Error", {}).get("Code", ""))
    return code in _MISSING_OBJECT_ERROR_CODES


def _read_json_bytes(s3_client: Any, bucket: str, key: str) -> bytes:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def _read_model_from_s3(
    s3_client: Any,
    bucket: str,
    key: str,
    model_class: type[Any],
) -> Any:
    return model_class.model_validate_json(_read_json_bytes(s3_client, bucket, key))


def _read_optional_model_from_s3(
    s3_client: Any,
    bucket: str,
    key: str,
    model_class: type[Any],
) -> Any | None:
    try:
        return _read_model_from_s3(s3_client, bucket, key, model_class)
    except Exception as error:
        if _is_missing_object_error(error):
            logger.info("Bronze object not available yet: s3://%s/%s", bucket, key)
            return None
        raise


def _boxscore_completeness(boxscore: BoxscoreResponse | None) -> DataCompleteness:
    if boxscore is None:
        return DataCompleteness.NONE

    teams = boxscore.liveData.linescore.teams
    stats = (
        teams.away.runs,
        teams.away.hits,
        teams.away.errors,
        teams.home.runs,
        teams.home.hits,
        teams.home.errors,
    )
    if any(value is None for value in stats):
        return DataCompleteness.PARTIAL
    return DataCompleteness.FULL


def build_silver_game(
    schedule_game: ScheduleGame,
    boxscore: BoxscoreResponse | None,
    content: ContentResponse | None,
) -> SilverGame | None:
    """Join Bronze schedule, boxscore, and content data into one Silver game."""
    try:
        linescore = (
            boxscore.liveData.linescore
            if boxscore is not None
            else schedule_game.linescore
        )
        away_boxscore_team = (
            boxscore.gameData.teams.away if boxscore is not None else None
        )
        home_boxscore_team = (
            boxscore.gameData.teams.home if boxscore is not None else None
        )
        decisions = boxscore.liveData.decisions if boxscore is not None else None

        payload = {
            "gamePk": schedule_game.gamePk,
            "date": _parse_timestamp(schedule_game.gameDate),
            "game_type": schedule_game.gameType,
            "game_number": schedule_game.gameNumber,
            "doubleheader_type": schedule_game.doubleHeader,
            "away_team_id": schedule_game.teams.away.team.id,
            "away_team_name": schedule_game.teams.away.team.name,
            "away_team_abbreviation": _team_abbreviation(
                schedule_game.teams.away.team.id,
                schedule_game.teams.away.team.name,
                away_boxscore_team.abbreviation
                if away_boxscore_team is not None
                else None,
            ),
            "home_team_id": schedule_game.teams.home.team.id,
            "home_team_name": schedule_game.teams.home.team.name,
            "home_team_abbreviation": _team_abbreviation(
                schedule_game.teams.home.team.id,
                schedule_game.teams.home.team.name,
                home_boxscore_team.abbreviation
                if home_boxscore_team is not None
                else None,
            ),
            "venue_id": schedule_game.venue.id,
            "venue_name": schedule_game.venue.name,
            "status": schedule_game.status.abstractGameState,
            "status_detail": schedule_game.status.detailedState,
            "current_inning": linescore.currentInning
            if linescore is not None
            else None,
            "inning_state": linescore.inningState if linescore is not None else None,
            "innings": (
                max(linescore.currentInning or 0, linescore.scheduledInnings)
                if linescore is not None
                else None
            ),
            "away_runs": linescore.teams.away.runs if linescore is not None else None,
            "away_hits": linescore.teams.away.hits if linescore is not None else None,
            "away_errors": (
                linescore.teams.away.errors if linescore is not None else None
            ),
            "home_runs": linescore.teams.home.runs if linescore is not None else None,
            "home_hits": linescore.teams.home.hits if linescore is not None else None,
            "home_errors": (
                linescore.teams.home.errors if linescore is not None else None
            ),
            "winning_pitcher_name": (
                decisions.winner.fullName
                if decisions is not None and decisions.winner is not None
                else None
            ),
            "losing_pitcher_name": (
                decisions.loser.fullName
                if decisions is not None and decisions.loser is not None
                else None
            ),
            "save_pitcher_name": (
                decisions.save.fullName
                if decisions is not None and decisions.save is not None
                else None
            ),
            "condensed_game_url": extract_condensed_game_url(content),
            "source_updated_at": _parse_source_updated_at(schedule_game, boxscore),
            "data_completeness": _boxscore_completeness(boxscore),
        }
        return SilverGame.model_validate(payload)
    except (ValidationError, ValueError):
        logger.exception(
            "Skipping invalid Silver game payload for gamePk=%s",
            schedule_game.gamePk,
        )
        return None


def _is_final_game(schedule_game: ScheduleGame) -> bool:
    return (
        schedule_game.status.abstractGameState == "Final"
        or schedule_game.status.detailedState == "Final"
    )


def build_master_schedule(
    s3_client: Any,
    bucket: str,
    year: int,
    execution_time: datetime | None = None,
) -> SilverMasterSchedule:
    """Read Bronze objects for a season and build the Silver master schedule."""
    schedule = _read_model_from_s3(
        s3_client,
        bucket,
        CatchPaths.bronze_schedule_key(year),
        ScheduleResponse,
    )
    silver_games: list[SilverGame] = []

    for schedule_date in schedule.dates:
        for schedule_game in schedule_date.games:
            if not _is_final_game(schedule_game):
                continue

            game_pk = schedule_game.gamePk
            boxscore = _read_optional_model_from_s3(
                s3_client,
                bucket,
                CatchPaths.bronze_boxscore_key(game_pk),
                BoxscoreResponse,
            )
            content = _read_optional_model_from_s3(
                s3_client,
                bucket,
                CatchPaths.bronze_content_key(game_pk),
                ContentResponse,
            )
            silver_game = build_silver_game(schedule_game, boxscore, content)
            if silver_game is not None:
                silver_games.append(silver_game)

    return SilverMasterSchedule(
        year=year,
        last_updated=execution_time or current_utc(),
        games=silver_games,
    )


def write_master_schedule_to_s3(
    s3_client: Any,
    bucket: str,
    master_schedule: SilverMasterSchedule,
) -> str:
    """Write a validated Silver master schedule JSON document to S3."""
    key = CatchPaths.silver_master_schedule_key(master_schedule.year)
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=master_schedule.model_dump_json(indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle S3 notifications by rebuilding the Silver master schedule."""
    del context

    year = extract_year_from_s3_event(event)
    bucket = os.environ.get("S3_BUCKET_NAME") or _bucket_name_from_event(event)
    s3_client = create_s3_client()

    master_schedule = build_master_schedule(s3_client, bucket, year, current_utc())
    output_key = write_master_schedule_to_s3(s3_client, bucket, master_schedule)

    return {
        "bucket": bucket,
        "games_written": len(master_schedule.games),
        "output_key": output_key,
        "year": year,
    }


@click.group()
def cli():
    """Silver layer processing pipeline CLI."""


@cli.command()
@click.option("--year", type=int, required=True, help="Season year to rebuild.")
@click.option(
    "--bucket",
    default=None,
    envvar="S3_BUCKET_NAME",
    help="S3 bucket containing Bronze and Silver objects.",
)
def process(year: int, bucket: str | None):
    """Rebuild the Silver master schedule for one season."""
    if not bucket:
        raise click.ClickException("Provide --bucket or set S3_BUCKET_NAME")

    s3_client = create_s3_client()
    master_schedule = build_master_schedule(s3_client, bucket, year, current_utc())
    output_key = write_master_schedule_to_s3(s3_client, bucket, master_schedule)

    click.echo(
        json.dumps(
            {
                "bucket": bucket,
                "games_written": len(master_schedule.games),
                "output_key": output_key,
                "year": year,
            },
        ),
    )


if __name__ == "__main__":
    cli()
