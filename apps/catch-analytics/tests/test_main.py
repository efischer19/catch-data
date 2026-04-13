"""Tests for Gold team schedule generation in catch-analytics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from io import BytesIO

from catch_models import CatchPaths, GoldTeamSchedule, SilverMasterSchedule
from click.testing import CliRunner

from app.main import (
    MLB_TEAM_DIRECTORY,
    build_team_schedule,
    build_team_schedules,
    cli,
    generate_team_schedules,
    lambda_handler,
)


class FakeS3Client:
    def __init__(self, objects: dict[tuple[str, str], bytes]):
        self.objects = dict(objects)
        self.put_calls: list[dict[str, str | bytes]] = []

    def get_object(self, *, Bucket: str, Key: str):
        return {"Body": BytesIO(self.objects[(Bucket, Key)])}

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]


def _game_payload(
    *,
    game_pk: int,
    date: str,
    away_team_id: int,
    away_team_name: str,
    away_team_abbreviation: str,
    home_team_id: int,
    home_team_name: str,
    home_team_abbreviation: str,
    venue_name: str,
    status: str,
    game_number: int = 1,
    away_runs: int | None = None,
    away_hits: int | None = None,
    away_errors: int | None = None,
    home_runs: int | None = None,
    home_hits: int | None = None,
    home_errors: int | None = None,
    condensed_game_url: str | None = None,
    data_completeness: str = "none",
) -> dict:
    return {
        "gamePk": game_pk,
        "date": date,
        "game_type": "R",
        "game_number": game_number,
        "doubleheader_type": "S" if game_number > 1 else "N",
        "away_team_id": away_team_id,
        "away_team_name": away_team_name,
        "away_team_abbreviation": away_team_abbreviation,
        "home_team_id": home_team_id,
        "home_team_name": home_team_name,
        "home_team_abbreviation": home_team_abbreviation,
        "venue_id": 3313,
        "venue_name": venue_name,
        "status": status,
        "status_detail": status,
        "current_inning": 9 if status == "Final" else None,
        "inning_state": "End" if status == "Final" else None,
        "innings": 9 if status == "Final" else None,
        "away_runs": away_runs,
        "away_hits": away_hits,
        "away_errors": away_errors,
        "home_runs": home_runs,
        "home_hits": home_hits,
        "home_errors": home_errors,
        "winning_pitcher_name": "Ace Winner" if status == "Final" else None,
        "losing_pitcher_name": "Tough Loss" if status == "Final" else None,
        "save_pitcher_name": "Door Closer" if status == "Final" else None,
        "condensed_game_url": condensed_game_url,
        "source_updated_at": "2026-04-10T12:00:00Z",
        "data_completeness": data_completeness,
    }


def _master_schedule() -> SilverMasterSchedule:
    payload = {
        "year": 2026,
        "last_updated": "2026-04-10T12:00:00Z",
        "games": [
            _game_payload(
                game_pk=5002,
                date="2026-04-03T23:05:00Z",
                away_team_id=147,
                away_team_name="New York Yankees",
                away_team_abbreviation="NYY",
                home_team_id=111,
                home_team_name="Boston Red Sox",
                home_team_abbreviation="BOS",
                venue_name="Fenway Park",
                status="Scheduled",
            ),
            _game_payload(
                game_pk=5001,
                date="2026-04-01T17:05:00Z",
                away_team_id=111,
                away_team_name="Boston Red Sox",
                away_team_abbreviation="BOS",
                home_team_id=147,
                home_team_name="New York Yankees",
                home_team_abbreviation="NYY",
                venue_name="Yankee Stadium",
                status="Final",
                away_runs=2,
                away_hits=6,
                away_errors=1,
                home_runs=5,
                home_hits=8,
                home_errors=0,
                condensed_game_url="https://mlb.example/condensed-game.mp4",
                data_completeness="full",
            ),
            _game_payload(
                game_pk=5004,
                date="2026-04-10T17:05:00Z",
                away_team_id=111,
                away_team_name="Boston Red Sox",
                away_team_abbreviation="BOS",
                home_team_id=147,
                home_team_name="New York Yankees",
                home_team_abbreviation="NYY",
                venue_name="Yankee Stadium",
                status="Scheduled",
                game_number=2,
            ),
            _game_payload(
                game_pk=5003,
                date="2026-04-10T17:05:00Z",
                away_team_id=111,
                away_team_name="Boston Red Sox",
                away_team_abbreviation="BOS",
                home_team_id=147,
                home_team_name="New York Yankees",
                home_team_abbreviation="NYY",
                venue_name="Yankee Stadium",
                status="Scheduled",
                game_number=1,
            ),
            _game_payload(
                game_pk=7001,
                date="2026-04-04T02:10:00Z",
                away_team_id=119,
                away_team_name="Los Angeles Dodgers",
                away_team_abbreviation="LAD",
                home_team_id=135,
                home_team_name="San Diego Padres",
                home_team_abbreviation="SD",
                venue_name="Petco Park",
                status="Scheduled",
            ),
        ],
    }
    return SilverMasterSchedule.model_validate(payload)


def test_build_team_schedule_filters_sorts_and_handles_doubleheaders():
    schedule = build_team_schedule(
        _master_schedule(),
        147,
        last_updated=datetime(2026, 4, 10, 12, 30, tzinfo=UTC),
    )

    assert schedule.team_id == 147
    assert schedule.team_name == "New York Yankees"
    assert schedule.team_abbreviation == "NYY"
    assert [game.game_pk for game in schedule.games] == [5001, 5002, 5003, 5004]
    assert [game.game_number for game in schedule.games[-2:]] == [1, 2]


def test_build_team_schedule_gold_model_fields_for_completed_and_future_games():
    schedule = build_team_schedule(
        _master_schedule(),
        147,
        last_updated=datetime(2026, 4, 10, 12, 30, tzinfo=UTC),
    )

    completed_game = schedule.games[0]
    assert completed_game.score is not None
    assert completed_game.score.away == 2
    assert completed_game.score.home == 5
    assert completed_game.score_display == "2-5"
    assert completed_game.boxscore_summary is not None
    assert completed_game.boxscore_summary.home_h == 8
    assert completed_game.condensed_game_url == "https://mlb.example/condensed-game.mp4"

    future_game = schedule.games[1]
    assert future_game.status == "Scheduled"
    assert future_game.venue_name == "Fenway Park"
    assert future_game.score is None
    assert future_game.score_display is None
    assert future_game.boxscore_summary is None
    assert future_game.condensed_game_url is None


def test_generate_team_schedules_reads_master_schedule_and_writes_all_30_files():
    master_schedule = _master_schedule()
    bucket = "test-bucket"
    fake_s3 = FakeS3Client(
        {
            (
                bucket,
                CatchPaths.silver_master_schedule_key(master_schedule.year),
            ): master_schedule.model_dump_json().encode("utf-8")
        }
    )

    schedules = generate_team_schedules(
        master_schedule.year,
        s3_client=fake_s3,
        bucket_name=bucket,
        last_updated=datetime(2026, 4, 10, 12, 30, tzinfo=UTC),
    )

    assert len(schedules) == 30
    assert len(fake_s3.put_calls) == 30
    assert {call["Key"] for call in fake_s3.put_calls} == {
        CatchPaths.gold_team_key(team_id) for team_id in MLB_TEAM_DIRECTORY
    }

    yankees_payload = json.loads(
        fake_s3.objects[(bucket, CatchPaths.gold_team_key(147))].decode("utf-8")
    )
    validated_yankees = GoldTeamSchedule.model_validate(yankees_payload)
    assert validated_yankees.team_id == 147
    assert [game.game_pk for game in validated_yankees.games] == [
        5001,
        5002,
        5003,
        5004,
    ]

    angels_payload = json.loads(
        fake_s3.objects[(bucket, CatchPaths.gold_team_key(108))].decode("utf-8")
    )
    validated_angels = GoldTeamSchedule.model_validate(angels_payload)
    assert validated_angels.team_name == "Los Angeles Angels"
    assert validated_angels.games == []


def test_build_team_schedules_reuses_single_timestamp_for_all_files():
    timestamp = datetime(2026, 4, 10, 12, 30, tzinfo=UTC)
    schedules = build_team_schedules(_master_schedule(), last_updated=timestamp)

    assert {schedule.last_updated for schedule in schedules.values()} == {timestamp}


def test_lambda_handler_and_cli_use_team_schedule_generation(monkeypatch):
    captured_years: list[int] = []

    def fake_generate(year: int):
        captured_years.append(year)
        return {
            147: GoldTeamSchedule(
                team_id=147,
                team_name="New York Yankees",
                team_abbreviation="NYY",
                season_year=year,
            )
        }

    monkeypatch.setattr("app.main.generate_team_schedules", fake_generate)

    result = lambda_handler({"year": 2026}, None)
    assert result == {"year": 2026, "team_schedule_count": 1}

    runner = CliRunner()
    cli_result = runner.invoke(cli, ["generate-team-schedules", "--year", "2027"])
    assert cli_result.exit_code == 0
    assert "Reading Silver master schedule for 2027" in cli_result.output
    assert "Wrote 1 Gold team schedule files" in cli_result.output
    assert captured_years == [2026, 2027]
