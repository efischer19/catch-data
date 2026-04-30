"""Tests for Gold team schedule generation in catch-analytics."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from catch_models import (
    CatchPaths,
    GoldTeamSchedule,
    GoldUpcomingGames,
    SilverMasterSchedule,
)
from click.testing import CliRunner

from app import main

_FIXED_NOW = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)
_INFRASTRUCTURE_MAIN_TF = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "main.tf"
)


class _Body:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    def __init__(
        self,
        objects: dict[str, bytes],
        *,
        read_overrides: dict[str, bytes] | None = None,
    ):
        self.objects = objects
        self.read_overrides = read_overrides or {}
        self.writes: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        del Bucket
        if Key in self.read_overrides:
            return {"Body": _Body(self.read_overrides[Key])}
        if Key in self.writes:
            return {"Body": _Body(self.writes[Key])}
        return {"Body": _Body(self.objects[Key])}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        del Bucket, ContentType
        self.writes[Key] = Body


class _FakeCloudFrontClient:
    def __init__(self):
        self.invalidations: list[dict] = []

    def create_invalidation(self, **kwargs) -> dict:
        self.invalidations.append(kwargs)
        return {"Invalidation": {"Id": "INV123"}}


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _silver_game(**overrides) -> dict:
    payload = {
        "gamePk": 745678,
        "date": "2026-07-04T17:05:00Z",
        "game_type": "R",
        "game_number": 1,
        "doubleheader_type": "N",
        "away_team_id": 111,
        "away_team_name": "Boston Red Sox",
        "away_team_abbreviation": "BOS",
        "home_team_id": 147,
        "home_team_name": "New York Yankees",
        "home_team_abbreviation": "NYY",
        "venue_id": 3313,
        "venue_name": "Yankee Stadium",
        "status": "Final",
        "status_detail": "Final",
        "current_inning": 9,
        "inning_state": "End",
        "innings": 9,
        "away_runs": 3,
        "away_hits": 7,
        "away_errors": 1,
        "home_runs": 5,
        "home_hits": 9,
        "home_errors": 0,
        "winning_pitcher_name": "Gerrit Cole",
        "losing_pitcher_name": "Chris Sale",
        "save_pitcher_name": "Clay Holmes",
        "condensed_game_url": "https://example.com/condensed-game.mp4",
        "source_updated_at": "2026-07-04T21:17:00Z",
        "data_completeness": "full",
    }
    payload.update(overrides)
    return payload


def _scheduled_silver_game(**overrides) -> dict:
    return _silver_game(
        away_runs=None,
        away_hits=None,
        away_errors=None,
        home_runs=None,
        home_hits=None,
        home_errors=None,
        winning_pitcher_name=None,
        losing_pitcher_name=None,
        save_pitcher_name=None,
        condensed_game_url=None,
        status="Scheduled",
        status_detail="Scheduled",
        current_inning=None,
        inning_state=None,
        innings=None,
        data_completeness="none",
        **overrides,
    )


def _master_schedule_payload(games: list[dict]) -> dict:
    return {
        "year": 2026,
        "last_updated": "2026-07-05T12:00:00Z",
        "games": games,
        "processing_errors": {"count": 0, "gamePks": []},
    }


def test_build_team_schedule_filters_sorts_and_keeps_doubleheaders():
    master_schedule = SilverMasterSchedule.model_validate(
        _master_schedule_payload(
            [
                _scheduled_silver_game(
                    gamePk=745679,
                    date="2026-07-04T23:05:00Z",
                    game_number=2,
                    doubleheader_type="Y",
                ),
                _silver_game(
                    gamePk=799000,
                    home_team_id=119,
                    home_team_name="Los Angeles Dodgers",
                    home_team_abbreviation="LAD",
                    away_team_id=112,
                    away_team_name="Chicago Cubs",
                    away_team_abbreviation="CHC",
                    venue_id=22,
                    venue_name="Dodger Stadium",
                ),
                _silver_game(),
                _scheduled_silver_game(
                    gamePk=745100,
                    date="2026-03-28T17:10:00Z",
                    away_team_id=147,
                    away_team_name="New York Yankees",
                    away_team_abbreviation="NYY",
                    home_team_id=121,
                    home_team_name="New York Mets",
                    home_team_abbreviation="NYM",
                    venue_id=3289,
                    venue_name="Citi Field",
                ),
            ]
        )
    )

    schedule = main.build_team_schedule(master_schedule, 147, execution_time=_FIXED_NOW)
    dumped = schedule.model_dump(mode="json", exclude_none=True)

    assert schedule.team_name == "New York Yankees"
    assert schedule.team_abbreviation == "NYY"
    assert dumped["last_updated"] == "2026-07-05T12:00:00Z"
    assert [game["game_pk"] for game in dumped["games"]] == [745100, 745678, 745679]
    assert [game["game_number"] for game in dumped["games"][-2:]] == [1, 2]
    assert all(
        game.home_team.id == 147 or game.away_team.id == 147 for game in schedule.games
    )
    assert dumped["games"][0]["venue_name"] == "Citi Field"
    assert dumped["games"][1]["score"] == {"away": 3, "home": 5}
    assert dumped["games"][1]["boxscore_summary"]["winning_pitcher"] == "Gerrit Cole"
    assert "score" not in dumped["games"][2]
    assert "condensed_game_url" not in dumped["games"][2]
    assert "boxscore_summary" not in dumped["games"][2]


def test_build_upcoming_games_filters_sorts_groups_and_keeps_boundaries():
    master_schedule = SilverMasterSchedule.model_validate(
        _master_schedule_payload(
            [
                _scheduled_silver_game(
                    gamePk=745001,
                    date="2026-07-03T23:59:00Z",
                ),
                _silver_game(),
                _scheduled_silver_game(
                    gamePk=745679,
                    date="2026-07-05T16:05:00Z",
                    away_team_id=121,
                    away_team_name="New York Mets",
                    away_team_abbreviation="NYM",
                    home_team_id=120,
                    home_team_name="Washington Nationals",
                    home_team_abbreviation="WSH",
                    venue_id=3309,
                    venue_name="Nationals Park",
                ),
                _scheduled_silver_game(
                    gamePk=745680,
                    date="2026-07-05T23:05:00Z",
                    away_team_id=119,
                    away_team_name="Los Angeles Dodgers",
                    away_team_abbreviation="LAD",
                    home_team_id=112,
                    home_team_name="Chicago Cubs",
                    home_team_abbreviation="CHC",
                    venue_id=22,
                    venue_name="Dodger Stadium",
                ),
                _scheduled_silver_game(
                    gamePk=745999,
                    date="2026-07-12T18:05:00Z",
                    game_type="F",
                    away_team_id=111,
                    away_team_name="Boston Red Sox",
                    away_team_abbreviation="BOS",
                    home_team_id=147,
                    home_team_name="New York Yankees",
                    home_team_abbreviation="NYY",
                    venue_id=3313,
                    venue_name="Yankee Stadium",
                ),
                _scheduled_silver_game(
                    gamePk=746000,
                    date="2026-07-13T00:05:00Z",
                ),
            ]
        )
    )

    upcoming = main.build_upcoming_games(
        master_schedule,
        execution_time=_FIXED_NOW,
        lookback_days=1,
        lookahead_days=7,
    )
    dumped = upcoming.model_dump(mode="json", exclude_none=True)

    assert [game["game_pk"] for game in dumped["games"]] == [
        745678,
        745679,
        745680,
        745999,
    ]
    assert dumped["games"][0]["score"] == {"away": 3, "home": 5}
    assert [group["date"] for group in dumped["dates"]] == [
        "2026-07-04",
        "2026-07-05",
        "2026-07-12",
    ]
    assert [game["game_pk"] for game in dumped["dates"][1]["games"]] == [745679, 745680]


def test_build_upcoming_games_uses_env_configurable_window(monkeypatch):
    master_schedule = SilverMasterSchedule.model_validate(
        _master_schedule_payload(
            [
                _silver_game(gamePk=745677, date="2026-07-04T01:05:00Z"),
                _silver_game(gamePk=745678, date="2026-07-05T17:05:00Z"),
                _silver_game(gamePk=745679, date="2026-07-06T17:05:00Z"),
                _silver_game(gamePk=745680, date="2026-07-07T17:05:00Z"),
            ]
        )
    )
    monkeypatch.setenv(main._UPCOMING_LOOKBACK_DAYS_ENV_VAR, "0")
    monkeypatch.setenv(main._UPCOMING_LOOKAHEAD_DAYS_ENV_VAR, "1")

    upcoming = main.build_upcoming_games(master_schedule, execution_time=_FIXED_NOW)

    assert [game.game_pk for game in upcoming.games] == [745678, 745679]


def test_build_upcoming_games_handles_no_games_today():
    master_schedule = SilverMasterSchedule.model_validate(
        _master_schedule_payload(
            [
                _silver_game(gamePk=745677, date="2026-07-04T17:05:00Z"),
                _scheduled_silver_game(
                    gamePk=745679,
                    date="2026-07-06T17:05:00Z",
                ),
            ]
        )
    )

    upcoming = main.build_upcoming_games(
        master_schedule,
        execution_time=_FIXED_NOW,
        lookback_days=1,
        lookahead_days=1,
    )
    dumped = upcoming.model_dump(mode="json", exclude_none=True)

    assert [group["date"] for group in dumped["dates"]] == ["2026-07-04", "2026-07-06"]
    assert "2026-07-05" not in {group["date"] for group in dumped["dates"]}


def test_build_upcoming_games_handles_end_of_season_window():
    season_end_now = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    master_schedule = SilverMasterSchedule.model_validate(
        _master_schedule_payload(
            [
                _silver_game(gamePk=800001, date="2026-09-29T20:05:00Z"),
                _silver_game(gamePk=800002, date="2026-09-30T20:05:00Z"),
                _scheduled_silver_game(
                    gamePk=800003,
                    date="2026-10-03T20:05:00Z",
                    game_type="F",
                ),
                _scheduled_silver_game(
                    gamePk=800004,
                    date="2026-10-08T20:05:00Z",
                    game_type="F",
                ),
                _scheduled_silver_game(
                    gamePk=800005,
                    date="2026-10-09T20:05:00Z",
                    game_type="F",
                ),
            ]
        )
    )

    upcoming = main.build_upcoming_games(
        master_schedule,
        execution_time=season_end_now,
        lookback_days=1,
        lookahead_days=7,
    )

    assert [game.game_pk for game in upcoming.games] == [800002, 800003, 800004]


def test_generate_team_schedule_files_writes_all_30_outputs_and_upcoming_file():
    fake_s3 = _FakeS3Client(
        {
            CatchPaths.silver_master_schedule_key(2026): _json_bytes(
                _master_schedule_payload([_silver_game()])
            )
        }
    )

    result = main.generate_team_schedule_files(
        fake_s3,
        "test-bucket",
        2026,
        execution_time=_FIXED_NOW,
    )

    assert result["team_schedule_count"] == 30
    assert result["upcoming_games_count"] == 1
    assert result["files_written"] == 31
    assert result["files_validated"] == 31
    assert result["files_failed"] == 0
    assert len(result["output_keys"]) == 31
    assert len(fake_s3.writes) == 31

    yankees = GoldTeamSchedule.model_validate_json(
        fake_s3.writes[CatchPaths.gold_team_key(147)]
    )
    angels = GoldTeamSchedule.model_validate_json(
        fake_s3.writes[CatchPaths.gold_team_key(108)]
    )
    upcoming = GoldUpcomingGames.model_validate_json(
        fake_s3.writes[CatchPaths.gold_upcoming_games_key()]
    )

    assert len(yankees.games) == 1
    assert angels.games == []
    assert angels.team_name == "Los Angeles Angels"
    assert angels.team_abbreviation == "LAA"
    assert len(upcoming.games) == 1
    assert len(upcoming.dates) == 1


def test_generate_team_schedule_files_logs_validation_failure_and_raises(caplog):
    failing_key = CatchPaths.gold_team_key(147)
    fake_s3 = _FakeS3Client(
        {
            CatchPaths.silver_master_schedule_key(2026): _json_bytes(
                _master_schedule_payload([_silver_game()])
            )
        },
        read_overrides={failing_key: b'{"team_id":"oops"}'},
    )

    with (
        caplog.at_level("INFO"),
        pytest.raises(
            RuntimeError,
            match="1 Gold files failed validation",
        ),
    ):
        main.generate_team_schedule_files(
            fake_s3,
            "test-bucket",
            2026,
            execution_time=_FIXED_NOW,
        )

    assert len(fake_s3.writes) == 31
    assert f"Gold output validation failed for {failing_key}" in caplog.text
    assert "files_written=31 files_validated=30 files_failed=1" in caplog.text


def test_generate_team_schedule_files_invalidates_cloudfront_when_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_s3 = _FakeS3Client(
        {
            CatchPaths.silver_master_schedule_key(2026): _json_bytes(
                _master_schedule_payload([_silver_game()])
            )
        }
    )
    fake_cloudfront = _FakeCloudFrontClient()
    monkeypatch.setenv(main._CLOUDFRONT_DISTRIBUTION_ID_ENV_VAR, "DIST123")
    monkeypatch.setattr(main, "create_cloudfront_client", lambda: fake_cloudfront)

    result = main.generate_team_schedule_files(
        fake_s3,
        "test-bucket",
        2026,
        execution_time=_FIXED_NOW,
    )

    assert result["cloudfront_invalidation_id"] == "INV123"
    assert fake_cloudfront.invalidations == [
        {
            "DistributionId": "DIST123",
            "InvalidationBatch": {
                "CallerReference": "gold-2026-07-05T12:00:00+00:00-31",
                "Paths": {
                    "Quantity": 31,
                    "Items": [f"/{key}" for key in result["output_keys"]],
                },
            },
        }
    ]


def test_terraform_configures_silver_to_gold_trigger():
    terraform = _INFRASTRUCTURE_MAIN_TF.read_text()

    assert 'resource "aws_lambda_permission" "allow_data_bucket_invoke"' in terraform
    assert re.search(
        r'resource\s+"aws_s3_bucket_notification"\s+"bronze_schedule_to_silver"',
        terraform,
    )
    assert re.search(
        r'lambda_function\s*\{[^}]*events\s*=\s*\["s3:ObjectCreated:\*"\][^}]*'
        r'filter_prefix\s*=\s*"silver/master_schedule_"',
        terraform,
        re.DOTALL,
    )


def test_lambda_handler_reads_event_key_and_bucket(monkeypatch):
    fake_s3 = _FakeS3Client(
        {
            CatchPaths.silver_master_schedule_key(2026): _json_bytes(
                _master_schedule_payload([_silver_game()])
            )
        }
    )
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3)
    monkeypatch.setattr(main, "current_utc", lambda: _FIXED_NOW)

    result = main.lambda_handler(
        {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "event-bucket"},
                        "object": {"key": "silver/master_schedule_2026.json"},
                    }
                }
            ]
        },
        object(),
    )

    assert result["bucket"] == "event-bucket"
    assert result["year"] == 2026
    assert result["team_schedule_count"] == 30
    assert result["upcoming_games_count"] == 1
    assert CatchPaths.gold_team_key(147) in result["output_keys"]
    assert CatchPaths.gold_upcoming_games_key() in result["output_keys"]


def test_cli_aggregate_outputs_json_summary(monkeypatch):
    fake_s3 = _FakeS3Client(
        {
            CatchPaths.silver_master_schedule_key(2026): _json_bytes(
                _master_schedule_payload([_silver_game()])
            )
        }
    )
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3)
    monkeypatch.setattr(main, "current_utc", lambda: _FIXED_NOW)

    result = CliRunner().invoke(
        main.cli,
        ["aggregate", "--year", "2026", "--bucket", "cli-bucket"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["team_schedule_count"] == 30
    assert json.loads(result.output)["upcoming_games_count"] == 1


def test_shared_content_fixture_is_available(sample_content):
    """Verify shared content fixtures can still be reused from the testing dir."""
    assert sample_content["link"].endswith("/content")
