"""Tests for the Silver layer Lambda in catch-processing."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from catch_models import ContentResponse, SilverGame, SilverMasterSchedule
from click.testing import CliRunner

from app import main


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (
            candidate / "libs" / "catch-models" / "tests" / "fixtures"
        ).exists():
            return candidate
    raise RuntimeError("Unable to locate repository root for shared test fixtures")


FIXTURES = _repo_root() / "libs" / "catch-models" / "tests" / "fixtures"


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


class _FakeClientError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class _FakeS3Client:
    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects
        self.writes: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str) -> dict:
        del Bucket
        if Key not in self.objects:
            raise _FakeClientError("NoSuchKey")
        return {"Body": _Body(self.objects[Key])}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        del Bucket, ContentType
        self.writes[Key] = Body


class _FakeSQSClient:
    def __init__(self):
        self.messages: list[dict[str, str]] = []

    def send_message(self, QueueUrl: str, MessageBody: str) -> None:
        self.messages.append({"QueueUrl": QueueUrl, "MessageBody": MessageBody})


def _json_bytes(payload: dict) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _build_test_silver_game(schedule_game: main.ScheduleGame) -> SilverGame:
    return SilverGame.model_validate(
        {
            "gamePk": schedule_game.gamePk,
            "date": schedule_game.gameDate,
            "game_type": schedule_game.gameType,
            "game_number": schedule_game.gameNumber,
            "doubleheader_type": schedule_game.doubleHeader,
            "away_team_id": schedule_game.teams.away.team.id,
            "away_team_name": schedule_game.teams.away.team.name,
            "away_team_abbreviation": "AWY",
            "home_team_id": schedule_game.teams.home.team.id,
            "home_team_name": schedule_game.teams.home.team.name,
            "home_team_abbreviation": "HME",
            "venue_id": schedule_game.venue.id,
            "venue_name": schedule_game.venue.name,
            "status": schedule_game.status.abstractGameState,
            "status_detail": schedule_game.status.detailedState,
            "current_inning": None,
            "inning_state": None,
            "innings": None,
            "away_runs": schedule_game.teams.away.score,
            "away_hits": None,
            "away_errors": None,
            "home_runs": schedule_game.teams.home.score,
            "home_hits": None,
            "home_errors": None,
            "winning_pitcher_name": None,
            "losing_pitcher_name": None,
            "save_pitcher_name": None,
            "condensed_game_url": None,
            "source_updated_at": schedule_game.gameDate,
            "data_completeness": "none",
        },
    )


def _make_schedule_with_games(total_games: int) -> dict:
    schedule = _load_fixture("schedule_typical.json")
    template = deepcopy(schedule["dates"][0]["games"][0])
    schedule["dates"] = [deepcopy(schedule["dates"][0])]
    schedule["dates"][0]["games"] = []
    for index in range(total_games):
        game = deepcopy(template)
        game["gamePk"] = 800000 + index
        game["gameDate"] = f"2024-06-{(index % 28) + 1:02d}T18:10:00Z"
        game["status"]["abstractGameState"] = "Final"
        game["status"]["detailedState"] = "Final"
        schedule["dates"][0]["games"].append(game)
    return schedule


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


def test_build_silver_game_logs_validation_errors_and_excludes_game(
    caplog: pytest.LogCaptureFixture,
):
    """Validation errors should be logged and the invalid game excluded."""
    schedule = main.ScheduleResponse.model_validate(
        _load_fixture("schedule_typical.json"),
    )
    schedule_game = (
        schedule.dates[0]
        .games[0]
        .model_copy(
            update={"doubleHeader": "X"},
        )
    )

    with caplog.at_level("WARNING"):
        silver_game = main.build_silver_game(schedule_game, None, None)

    assert silver_game is None
    assert '"event": "silver_game_excluded"' in caplog.text
    assert '"gamePk": 745678' in caplog.text
    assert '"error_type": "ValidationError"' in caplog.text


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
        "games_written": 2,
        "output_key": "silver/master_schedule_2024.json",
        "processing_errors_count": 0,
        "year": 2024,
    }

    written = SilverMasterSchedule.model_validate_json(
        fake_s3.writes["silver/master_schedule_2024.json"],
    )
    assert written.year == 2024
    assert written.last_updated == datetime(2026, 4, 13, 2, 30, 56, tzinfo=UTC)
    assert len(written.games) == 2
    assert written.processing_errors.count == 0
    assert written.games[0].game_pk == 745678
    assert str(written.games[0].condensed_game_url).endswith("condensed_745678.mp4")
    assert written.games[1].status == "Live"


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
    assert '"processing_errors_count": 0' in result.output


@pytest.mark.parametrize(
    ("total_games", "failing_games", "should_raise"),
    [(10, 1, False), (10, 2, True)],
)
def test_lambda_handler_applies_processing_failure_threshold(
    monkeypatch: pytest.MonkeyPatch,
    total_games: int,
    failing_games: int,
    should_raise: bool,
):
    """Partial failures should be tolerated below the configured threshold only."""
    schedule = _make_schedule_with_games(total_games)
    fake_s3 = _FakeS3Client({"bronze/schedule_2024.json": _json_bytes(schedule)})
    failing_game_pks = {800000 + index for index in range(failing_games)}

    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.delenv("SILVER_DLQ_URL", raising=False)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3)
    monkeypatch.setattr(
        main,
        "current_utc",
        lambda: datetime(2026, 4, 13, 2, 30, 56, tzinfo=UTC),
    )

    def _fake_build_silver_game(
        schedule_game: main.ScheduleGame,
        boxscore: main.BoxscoreResponse | None,
        content: main.ContentResponse | None,
    ) -> SilverGame | None:
        del boxscore, content
        if schedule_game.gamePk in failing_game_pks:
            return None
        return _build_test_silver_game(schedule_game)

    monkeypatch.setattr(main, "build_silver_game", _fake_build_silver_game)

    if should_raise:
        with pytest.raises(RuntimeError, match="failure rate exceeded threshold"):
            main.lambda_handler(_schedule_event("bronze/schedule_2024.json"), None)
        assert fake_s3.writes == {}
        return

    result = main.lambda_handler(_schedule_event("bronze/schedule_2024.json"), None)

    assert result["games_written"] == total_games - failing_games
    assert result["processing_errors_count"] == failing_games

    written = SilverMasterSchedule.model_validate_json(
        fake_s3.writes["silver/master_schedule_2024.json"],
    )
    assert len(written.games) == total_games - failing_games
    assert written.processing_errors.count == failing_games
    assert written.processing_errors.game_pks == sorted(failing_game_pks)


def test_build_master_schedule_rejects_duplicate_game_pks(
    monkeypatch: pytest.MonkeyPatch,
):
    """Duplicate game IDs should fail the Silver quality gate."""
    schedule = _make_schedule_with_games(2)
    schedule["dates"][0]["games"][1]["gamePk"] = schedule["dates"][0]["games"][0][
        "gamePk"
    ]
    fake_s3 = _FakeS3Client({"bronze/schedule_2024.json": _json_bytes(schedule)})

    monkeypatch.setattr(
        main,
        "build_silver_game",
        lambda schedule_game, boxscore, content: _build_test_silver_game(schedule_game),
    )

    with pytest.raises(RuntimeError, match="duplicate gamePk"):
        main.build_master_schedule(fake_s3, "test-bucket", 2024)


def test_lambda_handler_sends_failed_events_to_dlq(monkeypatch: pytest.MonkeyPatch):
    """Uncaught Lambda failures should be copied to the configured DLQ."""
    fake_sqs = _FakeSQSClient()
    queue_url = "https://sqs.us-west-2.amazonaws.com/123456789012/catch-processing-dlq"

    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("SILVER_DLQ_URL", queue_url)
    monkeypatch.setattr(main, "create_s3_client", lambda: object())
    monkeypatch.setattr(main, "create_sqs_client", lambda: fake_sqs)
    monkeypatch.setattr(
        main,
        "build_master_schedule",
        lambda *args: (_ for _ in ()).throw(RuntimeError("kaboom")),
    )
    monkeypatch.setattr(
        main,
        "current_utc",
        lambda: datetime(2026, 4, 13, 2, 30, 56, tzinfo=UTC),
    )

    event = _schedule_event("bronze/schedule_2024.json")

    with pytest.raises(RuntimeError, match="kaboom"):
        main.lambda_handler(event, None)

    assert fake_sqs.messages == [
        {
            "QueueUrl": queue_url,
            "MessageBody": json.dumps(
                {
                    "errorMessage": "kaboom",
                    "errorType": "RuntimeError",
                    "event": event,
                    "failedAt": "2026-04-13T02:30:56Z",
                },
                sort_keys=True,
            ),
        },
    ]


def test_write_to_s3_returns_count():
    """Verify the placeholder write returns the record count."""
    records = [{"entity_id": "1"}, {"entity_id": "2"}]
    count = main.write_to_s3(records, "silver/items/2026-01-15/")
    assert count == 2


def test_shared_boxscore_fixture_is_available(sample_boxscore):
    """Verify shared boxscore fixtures can be reused from the testing dir."""
    assert sample_boxscore["gameData"]["game"]["type"] == "R"
