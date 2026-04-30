"""Gold layer Lambda for generating Gold schedule JSON from Silver data."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import unquote_plus

import click
from catch_models import (
    CatchPaths,
    DataCompleteness,
    GoldBoxscoreSummary,
    GoldGameSummary,
    GoldScore,
    GoldTeamInfo,
    GoldTeamSchedule,
    GoldUpcomingGames,
    SilverMasterSchedule,
)

logger = logging.getLogger(__name__)

_MASTER_SCHEDULE_KEY_RE = re.compile(
    r"(^|/)silver/master_schedule_(?P<year>\d{4})\.json$"
)
_UPCOMING_LOOKBACK_DAYS_ENV_VAR = "GOLD_UPCOMING_GAMES_LOOKBACK_DAYS"
_UPCOMING_LOOKAHEAD_DAYS_ENV_VAR = "GOLD_UPCOMING_GAMES_LOOKAHEAD_DAYS"
_DEFAULT_UPCOMING_LOOKBACK_DAYS = 1
_DEFAULT_UPCOMING_LOOKAHEAD_DAYS = 7


@dataclass(frozen=True)
class TeamContext:
    name: str
    abbreviation: str
    league: str
    division: str


_MLB_TEAM_CONTEXT: dict[int, TeamContext] = {
    108: TeamContext("Los Angeles Angels", "LAA", "American League", "AL West"),
    109: TeamContext("Arizona Diamondbacks", "AZ", "National League", "NL West"),
    110: TeamContext("Baltimore Orioles", "BAL", "American League", "AL East"),
    111: TeamContext("Boston Red Sox", "BOS", "American League", "AL East"),
    112: TeamContext("Chicago Cubs", "CHC", "National League", "NL Central"),
    113: TeamContext("Cincinnati Reds", "CIN", "National League", "NL Central"),
    114: TeamContext("Cleveland Guardians", "CLE", "American League", "AL Central"),
    115: TeamContext("Colorado Rockies", "COL", "National League", "NL West"),
    116: TeamContext("Detroit Tigers", "DET", "American League", "AL Central"),
    117: TeamContext("Houston Astros", "HOU", "American League", "AL West"),
    118: TeamContext("Kansas City Royals", "KC", "American League", "AL Central"),
    119: TeamContext("Los Angeles Dodgers", "LAD", "National League", "NL West"),
    120: TeamContext("Washington Nationals", "WSH", "National League", "NL East"),
    121: TeamContext("New York Mets", "NYM", "National League", "NL East"),
    133: TeamContext("Oakland Athletics", "OAK", "American League", "AL West"),
    134: TeamContext("Pittsburgh Pirates", "PIT", "National League", "NL Central"),
    135: TeamContext("San Diego Padres", "SD", "National League", "NL West"),
    136: TeamContext("Seattle Mariners", "SEA", "American League", "AL West"),
    137: TeamContext("San Francisco Giants", "SF", "National League", "NL West"),
    138: TeamContext("St. Louis Cardinals", "STL", "National League", "NL Central"),
    139: TeamContext("Tampa Bay Rays", "TB", "American League", "AL East"),
    140: TeamContext("Texas Rangers", "TEX", "American League", "AL West"),
    141: TeamContext("Toronto Blue Jays", "TOR", "American League", "AL East"),
    142: TeamContext("Minnesota Twins", "MIN", "American League", "AL Central"),
    143: TeamContext("Philadelphia Phillies", "PHI", "National League", "NL East"),
    144: TeamContext("Atlanta Braves", "ATL", "National League", "NL East"),
    145: TeamContext("Chicago White Sox", "CWS", "American League", "AL Central"),
    146: TeamContext("Miami Marlins", "MIA", "National League", "NL East"),
    147: TeamContext("New York Yankees", "NYY", "American League", "AL East"),
    158: TeamContext("Milwaukee Brewers", "MIL", "National League", "NL Central"),
}
_MLB_TEAM_IDS = tuple(_MLB_TEAM_CONTEXT)


def create_s3_client():
    """Create an S3 client lazily so tests do not require boto3 installed."""
    import boto3

    return boto3.client("s3")


def current_utc() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(UTC)


def _first_s3_record(event: dict[str, Any]) -> dict[str, Any]:
    records = event.get("Records", [])
    if not records:
        raise ValueError("S3 event must include at least one record")
    return records[0]


def _bucket_name_from_event(event: dict[str, Any]) -> str:
    return _first_s3_record(event)["s3"]["bucket"]["name"]


def _bucket_from_env_or_event(event: dict[str, Any]) -> str:
    bucket = os.environ.get("S3_BUCKET_NAME")
    if bucket is None:
        return _bucket_name_from_event(event)
    if not bucket:
        raise ValueError("S3_BUCKET_NAME must not be empty when configured")
    return bucket


def extract_year_from_s3_event(event: dict[str, Any]) -> int:
    """Extract the season year from a Silver master schedule S3 event."""
    key = unquote_plus(_first_s3_record(event)["s3"]["object"]["key"])
    match = _MASTER_SCHEDULE_KEY_RE.search(key)
    if match is None:
        raise ValueError(f"Unsupported S3 event key for Gold schedule build: {key}")
    return int(match.group("year"))


def read_master_schedule_from_s3(
    s3_client: Any,
    bucket: str,
    year: int,
) -> SilverMasterSchedule:
    """Read and validate the Silver master schedule for a season."""
    response = s3_client.get_object(
        Bucket=bucket,
        Key=CatchPaths.silver_master_schedule_key(year),
    )
    return SilverMasterSchedule.model_validate_json(response["Body"].read())


def _team_context(team_id: int) -> TeamContext:
    try:
        return _MLB_TEAM_CONTEXT[team_id]
    except KeyError as error:
        raise ValueError(f"Unsupported MLB team id: {team_id}") from error


def _build_team_info(team_id: int, name: str, abbreviation: str) -> GoldTeamInfo:
    context = _team_context(team_id)
    return GoldTeamInfo(
        id=team_id,
        name=name,
        abbreviation=abbreviation,
        league=context.league,
        division=context.division,
    )


def _build_boxscore_summary(silver_game) -> GoldBoxscoreSummary | None:
    required_totals = (
        silver_game.away_runs,
        silver_game.away_hits,
        silver_game.away_errors,
        silver_game.home_runs,
        silver_game.home_hits,
        silver_game.home_errors,
    )
    if silver_game.data_completeness is not DataCompleteness.FULL or any(
        value is None for value in required_totals
    ):
        return None

    return GoldBoxscoreSummary(
        away_r=silver_game.away_runs,
        away_h=silver_game.away_hits,
        away_e=silver_game.away_errors,
        home_r=silver_game.home_runs,
        home_h=silver_game.home_hits,
        home_e=silver_game.home_errors,
        winning_pitcher=silver_game.winning_pitcher_name,
        losing_pitcher=silver_game.losing_pitcher_name,
        save_pitcher=silver_game.save_pitcher_name,
    )


def _build_gold_game_summary(silver_game) -> GoldGameSummary:
    has_score = silver_game.away_runs is not None and silver_game.home_runs is not None
    score = (
        GoldScore(away=silver_game.away_runs, home=silver_game.home_runs)
        if has_score
        else None
    )

    return GoldGameSummary(
        game_pk=silver_game.game_pk,
        date=silver_game.date,
        status=silver_game.status_detail,
        game_number=silver_game.game_number,
        venue_name=silver_game.venue_name,
        home_team=_build_team_info(
            silver_game.home_team_id,
            silver_game.home_team_name,
            silver_game.home_team_abbreviation,
        ),
        away_team=_build_team_info(
            silver_game.away_team_id,
            silver_game.away_team_name,
            silver_game.away_team_abbreviation,
        ),
        score=score,
        score_display=(
            f"{silver_game.away_runs}-{silver_game.home_runs}" if has_score else None
        ),
        condensed_game_url=(
            str(silver_game.condensed_game_url)
            if silver_game.condensed_game_url is not None
            else None
        ),
        boxscore_summary=_build_boxscore_summary(silver_game),
    )


def _team_name_and_abbreviation(
    team_id: int,
    filtered_games: list[Any],
) -> tuple[str, str]:
    for game in filtered_games:
        if game.home_team_id == team_id:
            return game.home_team_name, game.home_team_abbreviation
        if game.away_team_id == team_id:
            return game.away_team_name, game.away_team_abbreviation

    context = _team_context(team_id)
    return context.name, context.abbreviation


def _validate_non_negative_days(label: str, value: int) -> int:
    if value < 0:
        raise ValueError(f"{label} must be non-negative")
    return value


def _window_days_from_env(env_var: str, default: int) -> int:
    raw_value = os.environ.get(env_var)
    if raw_value is None:
        return default
    if raw_value == "":
        raise ValueError(f"{env_var} must not be empty when configured")
    try:
        parsed_value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{env_var} must be an integer") from error
    return _validate_non_negative_days(env_var, parsed_value)


def _upcoming_window_bounds(
    execution_time: datetime,
    lookback_days: int,
    lookahead_days: int,
) -> tuple[date, date]:
    anchor_date = execution_time.astimezone(UTC).date()
    return (
        anchor_date - timedelta(days=lookback_days),
        anchor_date + timedelta(days=lookahead_days),
    )


def build_team_schedule(
    master_schedule: SilverMasterSchedule,
    team_id: int,
    execution_time: datetime | None = None,
) -> GoldTeamSchedule:
    """Build a validated Gold schedule for one MLB team."""
    filtered_games = sorted(
        (
            game
            for game in master_schedule.games
            if game.home_team_id == team_id or game.away_team_id == team_id
        ),
        key=lambda game: (game.date, game.game_number, game.game_pk),
    )
    team_name, team_abbreviation = _team_name_and_abbreviation(team_id, filtered_games)

    return GoldTeamSchedule(
        team_id=team_id,
        team_name=team_name,
        team_abbreviation=team_abbreviation,
        season_year=master_schedule.year,
        last_updated=execution_time or current_utc(),
        games=[_build_gold_game_summary(game) for game in filtered_games],
    )


def build_all_team_schedules(
    master_schedule: SilverMasterSchedule,
    execution_time: datetime | None = None,
) -> list[GoldTeamSchedule]:
    """Build schedules for all 30 MLB teams using a shared timestamp."""
    timestamp = execution_time or current_utc()
    return [
        build_team_schedule(master_schedule, team_id, execution_time=timestamp)
        for team_id in _MLB_TEAM_IDS
    ]


def build_upcoming_games(
    master_schedule: SilverMasterSchedule,
    execution_time: datetime | None = None,
    lookback_days: int | None = None,
    lookahead_days: int | None = None,
) -> GoldUpcomingGames:
    """Build the rolling-window Gold upcoming-games view."""
    timestamp = execution_time or current_utc()
    resolved_lookback_days = (
        _validate_non_negative_days("lookback_days", lookback_days)
        if lookback_days is not None
        else _window_days_from_env(
            _UPCOMING_LOOKBACK_DAYS_ENV_VAR,
            _DEFAULT_UPCOMING_LOOKBACK_DAYS,
        )
    )
    resolved_lookahead_days = (
        _validate_non_negative_days("lookahead_days", lookahead_days)
        if lookahead_days is not None
        else _window_days_from_env(
            _UPCOMING_LOOKAHEAD_DAYS_ENV_VAR,
            _DEFAULT_UPCOMING_LOOKAHEAD_DAYS,
        )
    )
    window_start, window_end = _upcoming_window_bounds(
        timestamp,
        resolved_lookback_days,
        resolved_lookahead_days,
    )
    filtered_games = sorted(
        (
            game
            for game in master_schedule.games
            if window_start <= game.date.date() <= window_end
        ),
        key=lambda game: (game.date, game.game_number, game.game_pk),
    )
    return GoldUpcomingGames(
        last_updated=timestamp,
        games=[_build_gold_game_summary(game) for game in filtered_games],
    )


def write_team_schedules_to_s3(
    s3_client: Any,
    bucket: str,
    team_schedules: list[GoldTeamSchedule],
) -> list[str]:
    """Serialize validated Gold team schedules and write them to S3."""
    output_keys: list[str] = []

    for schedule in team_schedules:
        key = CatchPaths.gold_team_key(schedule.team_id)
        body = json.dumps(
            schedule.model_dump(mode="json", exclude_none=True),
            separators=(",", ":"),
        ).encode("utf-8")
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        output_keys.append(key)

    return output_keys


def write_upcoming_games_to_s3(
    s3_client: Any,
    bucket: str,
    upcoming_games: GoldUpcomingGames,
) -> str:
    """Serialize validated Gold upcoming games and write them to S3."""
    key = CatchPaths.gold_upcoming_games_key()
    body = json.dumps(
        upcoming_games.model_dump(mode="json", exclude_none=True),
        separators=(",", ":"),
    ).encode("utf-8")
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    return key


def generate_team_schedule_files(
    s3_client: Any,
    bucket: str,
    year: int,
    execution_time: datetime | None = None,
) -> dict[str, Any]:
    """Build and write the Gold team schedules and upcoming-games view."""
    master_schedule = read_master_schedule_from_s3(s3_client, bucket, year)
    timestamp = execution_time or current_utc()
    team_schedules = build_all_team_schedules(master_schedule, timestamp)
    upcoming_games = build_upcoming_games(master_schedule, timestamp)
    output_keys = write_team_schedules_to_s3(s3_client, bucket, team_schedules)
    output_keys.append(write_upcoming_games_to_s3(s3_client, bucket, upcoming_games))

    return {
        "bucket": bucket,
        "output_keys": output_keys,
        "team_schedule_count": len(team_schedules),
        "upcoming_games_count": len(upcoming_games.games),
        "year": master_schedule.year,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle S3 notifications by rebuilding all Gold team schedules."""
    del context

    year = extract_year_from_s3_event(event)
    bucket = _bucket_from_env_or_event(event)
    return generate_team_schedule_files(create_s3_client(), bucket, year, current_utc())


@click.group()
def cli():
    """Gold layer analytics pipeline CLI."""


@cli.command()
@click.option("--year", type=int, required=True, help="Season year to rebuild.")
@click.option(
    "--bucket",
    default=None,
    envvar="S3_BUCKET_NAME",
    help="S3 bucket containing Silver and Gold objects.",
)
def aggregate(year: int, bucket: str | None):
    """Build Gold JSON files from the Silver master schedule."""
    if not bucket:
        raise click.ClickException("Provide --bucket or set S3_BUCKET_NAME")

    result = generate_team_schedule_files(
        create_s3_client(),
        bucket,
        year,
        current_utc(),
    )
    click.echo(json.dumps(result))


if __name__ == "__main__":
    cli()
