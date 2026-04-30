"""Tests for Gold team schedule generation in catch-analytics."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from catch_models import CatchPaths, GoldTeamSchedule, SilverMasterSchedule
from click.testing import CliRunner

from app import main

_FIXED_NOW = datetime(2026, 7, 5, 12, 0, tzinfo=UTC)


class _Body:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects
        self.writes: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        del Bucket
        return {"Body": _Body(self.objects[Key])}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        del Bucket, ContentType
        self.writes[Key] = Body


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
                _silver_game(
                    gamePk=745679,
                    date="2026-07-04T23:05:00Z",
                    game_number=2,
                    doubleheader_type="Y",
                    status="Scheduled",
                    status_detail="Scheduled",
                    current_inning=None,
                    inning_state=None,
                    innings=None,
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
                    data_completeness="none",
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
                _silver_game(
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


def test_generate_team_schedule_files_writes_all_30_outputs():
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
    assert len(result["output_keys"]) == 30
    assert len(fake_s3.writes) == 30

    yankees = GoldTeamSchedule.model_validate_json(
        fake_s3.writes[CatchPaths.gold_team_key(147)]
    )
    angels = GoldTeamSchedule.model_validate_json(
        fake_s3.writes[CatchPaths.gold_team_key(108)]
    )

    assert len(yankees.games) == 1
    assert angels.games == []
    assert angels.team_name == "Los Angeles Angels"
    assert angels.team_abbreviation == "LAA"


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
    assert CatchPaths.gold_team_key(147) in result["output_keys"]


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


def test_shared_content_fixture_is_available(sample_content):
    """Verify shared content fixtures can still be reused from the testing dir."""
    assert sample_content["link"].endswith("/content")
