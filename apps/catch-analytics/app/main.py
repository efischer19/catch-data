"""Gold layer analytics pipeline for team schedule JSON generation."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Any

import click
from catch_models import (
    CatchPaths,
    DataCompleteness,
    GoldBoxscoreSummary,
    GoldGameSummary,
    GoldScore,
    GoldTeamInfo,
    GoldTeamSchedule,
    SilverGame,
    SilverMasterSchedule,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TeamDirectoryEntry:
    """Fallback metadata for the 30 MLB teams."""

    team_id: int
    team_name: str
    team_abbreviation: str
    league: str
    division: str


def _team_entry(
    team_id: int,
    team_name: str,
    team_abbreviation: str,
    league: str,
    division: str,
) -> TeamDirectoryEntry:
    return TeamDirectoryEntry(team_id, team_name, team_abbreviation, league, division)


MLB_TEAM_DIRECTORY: dict[int, TeamDirectoryEntry] = {
    108: _team_entry(108, "Los Angeles Angels", "LAA", "American League", "AL West"),
    109: _team_entry(109, "Arizona Diamondbacks", "AZ", "National League", "NL West"),
    110: _team_entry(110, "Baltimore Orioles", "BAL", "American League", "AL East"),
    111: _team_entry(111, "Boston Red Sox", "BOS", "American League", "AL East"),
    112: _team_entry(112, "Chicago Cubs", "CHC", "National League", "NL Central"),
    113: _team_entry(113, "Cincinnati Reds", "CIN", "National League", "NL Central"),
    114: _team_entry(
        114,
        "Cleveland Guardians",
        "CLE",
        "American League",
        "AL Central",
    ),
    115: _team_entry(115, "Colorado Rockies", "COL", "National League", "NL West"),
    116: _team_entry(116, "Detroit Tigers", "DET", "American League", "AL Central"),
    117: _team_entry(117, "Houston Astros", "HOU", "American League", "AL West"),
    118: _team_entry(118, "Kansas City Royals", "KC", "American League", "AL Central"),
    119: _team_entry(119, "Los Angeles Dodgers", "LAD", "National League", "NL West"),
    120: _team_entry(120, "Washington Nationals", "WSH", "National League", "NL East"),
    121: _team_entry(121, "New York Mets", "NYM", "National League", "NL East"),
    133: _team_entry(133, "Oakland Athletics", "ATH", "American League", "AL West"),
    134: _team_entry(134, "Pittsburgh Pirates", "PIT", "National League", "NL Central"),
    135: _team_entry(135, "San Diego Padres", "SD", "National League", "NL West"),
    136: _team_entry(136, "Seattle Mariners", "SEA", "American League", "AL West"),
    137: _team_entry(137, "San Francisco Giants", "SF", "National League", "NL West"),
    138: _team_entry(
        138,
        "St. Louis Cardinals",
        "STL",
        "National League",
        "NL Central",
    ),
    139: _team_entry(139, "Tampa Bay Rays", "TB", "American League", "AL East"),
    140: _team_entry(140, "Texas Rangers", "TEX", "American League", "AL West"),
    141: _team_entry(141, "Toronto Blue Jays", "TOR", "American League", "AL East"),
    142: _team_entry(142, "Minnesota Twins", "MIN", "American League", "AL Central"),
    143: _team_entry(143, "Philadelphia Phillies", "PHI", "National League", "NL East"),
    144: _team_entry(144, "Atlanta Braves", "ATL", "National League", "NL East"),
    145: _team_entry(145, "Chicago White Sox", "CWS", "American League", "AL Central"),
    146: _team_entry(146, "Miami Marlins", "MIA", "National League", "NL East"),
    147: _team_entry(147, "New York Yankees", "NYY", "American League", "AL East"),
    158: _team_entry(158, "Milwaukee Brewers", "MIL", "National League", "NL Central"),
}


def _bucket_name(bucket_name: str | None = None) -> str:
    return bucket_name or os.environ.get("S3_BUCKET_NAME", "catch-data-data-dev")


def _create_s3_client() -> Any:
    import boto3

    return boto3.client("s3")


def _team_directory_entry(team_id: int) -> TeamDirectoryEntry:
    try:
        return MLB_TEAM_DIRECTORY[team_id]
    except KeyError as exc:
        msg = f"unknown MLB team id: {team_id}"
        raise ValueError(msg) from exc


def _gold_team_info(
    team_id: int, team_name: str, team_abbreviation: str
) -> GoldTeamInfo:
    team = _team_directory_entry(team_id)
    return GoldTeamInfo(
        id=team_id,
        name=team_name,
        abbreviation=team_abbreviation,
        league=team.league,
        division=team.division,
    )


def _score_for_game(game: SilverGame) -> GoldScore | None:
    if game.away_runs is None or game.home_runs is None:
        return None
    return GoldScore(away=game.away_runs, home=game.home_runs)


def _boxscore_for_game(game: SilverGame) -> GoldBoxscoreSummary | None:
    stats = (
        game.away_runs,
        game.away_hits,
        game.away_errors,
        game.home_runs,
        game.home_hits,
        game.home_errors,
    )
    if game.data_completeness is not DataCompleteness.FULL or any(
        value is None for value in stats
    ):
        return None

    return GoldBoxscoreSummary(
        away_r=game.away_runs,
        away_h=game.away_hits,
        away_e=game.away_errors,
        home_r=game.home_runs,
        home_h=game.home_hits,
        home_e=game.home_errors,
        winning_pitcher=game.winning_pitcher_name,
        losing_pitcher=game.losing_pitcher_name,
        save_pitcher=game.save_pitcher_name,
    )


def build_gold_game_summary(game: SilverGame) -> GoldGameSummary:
    """Transform one Silver game into the frontend-facing Gold summary model."""

    score = _score_for_game(game)
    return GoldGameSummary(
        game_pk=game.game_pk,
        date=game.date,
        status=game.status,
        game_number=game.game_number,
        venue_name=game.venue_name,
        home_team=_gold_team_info(
            team_id=game.home_team_id,
            team_name=game.home_team_name,
            team_abbreviation=game.home_team_abbreviation,
        ),
        away_team=_gold_team_info(
            team_id=game.away_team_id,
            team_name=game.away_team_name,
            team_abbreviation=game.away_team_abbreviation,
        ),
        score=score,
        score_display=f"{score.away}-{score.home}" if score else None,
        condensed_game_url=(
            str(game.condensed_game_url) if game.condensed_game_url else None
        ),
        boxscore_summary=_boxscore_for_game(game),
    )


def read_master_schedule(
    year: int,
    *,
    s3_client: Any | None = None,
    bucket_name: str | None = None,
) -> SilverMasterSchedule:
    """Read and validate the Silver master schedule for a season."""

    client = s3_client or _create_s3_client()
    key = CatchPaths.silver_master_schedule_key(year)
    response = client.get_object(Bucket=_bucket_name(bucket_name), Key=key)
    return SilverMasterSchedule.model_validate_json(response["Body"].read())


def _team_schedule_identity(
    team_id: int, team_games: list[SilverGame]
) -> tuple[str, str]:
    for game in team_games:
        if game.home_team_id == team_id:
            return game.home_team_name, game.home_team_abbreviation
        if game.away_team_id == team_id:
            return game.away_team_name, game.away_team_abbreviation

    fallback = _team_directory_entry(team_id)
    return fallback.team_name, fallback.team_abbreviation


def build_team_schedule(
    master_schedule: SilverMasterSchedule,
    team_id: int,
    *,
    last_updated: datetime | None = None,
) -> GoldTeamSchedule:
    """Build one team's Gold schedule from the season-wide Silver schedule."""

    team_games = [
        game
        for game in master_schedule.games
        if game.home_team_id == team_id or game.away_team_id == team_id
    ]
    team_games.sort(key=lambda game: (game.date, game.game_number, game.game_pk))

    team_name, team_abbreviation = _team_schedule_identity(team_id, team_games)
    return GoldTeamSchedule(
        team_id=team_id,
        team_name=team_name,
        team_abbreviation=team_abbreviation,
        season_year=master_schedule.year,
        last_updated=last_updated or datetime.now(UTC),
        games=[build_gold_game_summary(game) for game in team_games],
    )


def build_team_schedules(
    master_schedule: SilverMasterSchedule,
    *,
    last_updated: datetime | None = None,
) -> dict[int, GoldTeamSchedule]:
    """Build schedules for all 30 MLB teams in one pass."""

    timestamp = last_updated or datetime.now(UTC)
    return {
        team_id: build_team_schedule(
            master_schedule,
            team_id,
            last_updated=timestamp,
        )
        for team_id in MLB_TEAM_DIRECTORY
    }


def write_team_schedules(
    schedules: dict[int, GoldTeamSchedule],
    *,
    s3_client: Any | None = None,
    bucket_name: str | None = None,
) -> int:
    """Validate and write Gold team schedules to S3."""

    client = s3_client or _create_s3_client()
    bucket = _bucket_name(bucket_name)

    for team_id, schedule in schedules.items():
        validated = GoldTeamSchedule.model_validate(schedule)
        body = json.dumps(
            validated.model_dump(mode="json", exclude_none=True),
            separators=(",", ":"),
        ).encode("utf-8")
        client.put_object(
            Bucket=bucket,
            Key=CatchPaths.gold_team_key(team_id),
            Body=body,
            ContentType="application/json",
        )

    return len(schedules)


def generate_team_schedules(
    year: int,
    *,
    s3_client: Any | None = None,
    bucket_name: str | None = None,
    last_updated: datetime | None = None,
) -> dict[int, GoldTeamSchedule]:
    """Read Silver schedule data, build 30 team schedules, and write Gold JSON."""

    master_schedule = read_master_schedule(
        year,
        s3_client=s3_client,
        bucket_name=bucket_name,
    )
    schedules = build_team_schedules(master_schedule, last_updated=last_updated)
    write_team_schedules(
        schedules,
        s3_client=s3_client,
        bucket_name=bucket_name,
    )
    logger.info("Wrote %d team schedules for %s", len(schedules), year)
    return schedules


def lambda_handler(event: dict[str, Any] | None, _context: Any) -> dict[str, Any]:
    """AWS Lambda entrypoint for Gold team schedule generation."""

    raw_year = (event or {}).get("year", date_type.today().year)
    year = int(raw_year)
    schedules = generate_team_schedules(year)
    return {
        "year": year,
        "team_schedule_count": len(schedules),
    }


@click.group()
def cli():
    """Gold layer analytics pipeline CLI."""


@cli.command("generate-team-schedules")
@click.option(
    "--year",
    type=int,
    default=date_type.today().year,
    show_default=True,
    help="Season year to transform from silver/master_schedule_{year}.json.",
)
def generate_team_schedules_command(year: int):
    """Generate Gold team schedule files for all 30 MLB teams."""

    click.echo(f"Reading Silver master schedule for {year}")
    schedules = generate_team_schedules(year)
    click.echo(f"Wrote {len(schedules)} Gold team schedule files")


if __name__ == "__main__":
    cli()
