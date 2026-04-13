"""Tests for the Silver layer Lambda in catch-processing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from catch_models import ContentResponse, SilverMasterSchedule
from click.testing import CliRunner

from app import main

FIXTURES = (
    Path(__file__).resolve().parents[3] / "libs" / "catch-models" / "tests" / "fixtures"
)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _schedule_event(key: str, bucket: str = "test-bucket") -> dict:
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key},
                },
            },
        ],
    }


class _Body:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload


class _FakeS3Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects
        self.writes: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        del Bucket
        if Key not in self.objects:
            raise KeyError(Key)
        return {"Body": _Body(self.objects[Key])}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        del Bucket, ContentType
        self.writes[Key] = Body


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def test_extract_year_from_s3_event_uses_schedule_key():
    """The Lambda should rebuild the season named in the uploaded schedule key."""
    event = _schedule_event("bronze/schedule_2024.json")

    assert main.extract_year_from_s3_event(event) == 2024


def test_build_silver_game_joins_boxscore_fields_and_normalizes_timestamps():
    """Final games should flatten boxscore metadata into SilverGame fields."""
    schedule_game = main.ScheduleResponse.model_validate(
        _load_fixture("schedule_typical.json"),
    )
    boxscore = main.BoxscoreResponse.model_validate(
        _load_fixture("boxscore_typical.json"),
    )

    silver_game = main.build_silver_game(
        schedule_game.dates[0].games[0],
        boxscore,
        None,
    )

    assert silver_game is not None
    dumped = silver_game.model_dump(mode="json")
    assert dumped["gamePk"] == 745678
    assert dumped["away_team_abbreviation"] == "NYY"
    assert dumped["home_team_abbreviation"] == "BOS"
    assert dumped["away_runs"] == 5
    assert dumped["home_hits"] == 8
    assert dumped["home_errors"] == 1
    assert dumped["winning_pitcher_name"] == "Gerrit Cole"
    assert dumped["losing_pitcher_name"] == "Brayan Bello"
    assert dumped["save_pitcher_name"] == "Clay Holmes"
    assert dumped["date"] == "2024-06-15T18:10:00Z"
    assert dumped["source_updated_at"] == "2024-06-15T22:15:00Z"
    assert dumped["data_completeness"] == "full"


def test_extract_condensed_game_url_prefers_extended_highlights_mp4avc():
    """Content joins should find the condensed-game style MP4 URL."""
    content = ContentResponse.model_validate(_load_fixture("content_typical.json"))

    assert (
        main.extract_condensed_game_url(content)
        == "https://cuts.diamond.mlb.com/FORGE/2024/2024-06/15/745678/condensed_745678.mp4"
    )


def test_build_silver_game_handles_missing_boxscore_and_content():
    """Missing Bronze enrichments should leave optional Silver fields null."""
    schedule = main.ScheduleResponse.model_validate(
        _load_fixture("schedule_typical.json"),
    )

    silver_game = main.build_silver_game(schedule.dates[1].games[0], None, None)

    assert silver_game is not None
    dumped = silver_game.model_dump(mode="json")
    assert dumped["gamePk"] == 745700
    assert dumped["away_team_abbreviation"] == "LAD"
    assert dumped["home_team_abbreviation"] == "SF"
    assert dumped["away_runs"] == 2
    assert dumped["home_runs"] == 7
    assert dumped["winning_pitcher_name"] is None
    assert dumped["condensed_game_url"] is None
    assert dumped["source_updated_at"] == "2024-06-16T23:05:00Z"
    assert dumped["data_completeness"] == "none"


def test_lambda_handler_reads_bronze_schedule_and_writes_master_schedule(
    monkeypatch: pytest.MonkeyPatch,
):
    """The Lambda should rebuild and persist a validated Silver master schedule."""
    schedule = _load_fixture("schedule_typical.json")
    schedule["dates"][1]["games"][0]["status"]["abstractGameState"] = "Live"
    schedule["dates"][1]["games"][0]["status"]["detailedState"] = "In Progress"

    fake_s3 = _FakeS3Client(
        {
            "bronze/schedule_2024.json": _json_bytes(schedule),
            "bronze/boxscore_745678.json": _json_bytes(
                _load_fixture("boxscore_typical.json"),
            ),
            "bronze/content_745678.json": _json_bytes(
                _load_fixture("content_typical.json"),
            ),
        },
    )
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3)
    monkeypatch.setattr(
        main,
        "current_utc",
        lambda: datetime(2026, 4, 13, 2, 30, 56, tzinfo=UTC),
    )

    result = main.lambda_handler(_schedule_event("bronze/schedule_2024.json"), None)

    assert result == {
        "bucket": "test-bucket",
        "games_written": 1,
        "output_key": "silver/master_schedule_2024.json",
        "year": 2024,
    }

    written = SilverMasterSchedule.model_validate_json(
        fake_s3.writes["silver/master_schedule_2024.json"],
    )
    assert written.year == 2024
    assert written.last_updated == datetime(2026, 4, 13, 2, 30, 56, tzinfo=UTC)
    assert len(written.games) == 1
    assert written.games[0].game_pk == 745678
    assert str(written.games[0].condensed_game_url).endswith("condensed_745678.mp4")


def test_cli_process_rebuilds_master_schedule(monkeypatch: pytest.MonkeyPatch):
    """The CLI should expose the same Silver rebuild path as the Lambda."""
    fake_schedule = SilverMasterSchedule(
        year=2024,
        last_updated=datetime(2026, 4, 13, 2, 30, 56, tzinfo=UTC),
        games=[],
    )
    runner = CliRunner()

    monkeypatch.setattr(main, "create_s3_client", lambda: object())
    monkeypatch.setattr(main, "build_master_schedule", lambda *args: fake_schedule)
    monkeypatch.setattr(
        main,
        "write_master_schedule_to_s3",
        (
            lambda s3_client, bucket, schedule: (
                f"silver/master_schedule_{schedule.year}.json"
            )
        ),
    )

    result = runner.invoke(
        main.cli,
        ["process", "--year", "2024", "--bucket", "test-bucket"],
    )

    assert result.exit_code == 0
    assert '"games_written": 0' in result.output
