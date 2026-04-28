"""Tests for the catch-ingestion Bronze ingestion CLI."""

from __future__ import annotations

import json
import logging
from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import click
import pytest
import requests
from botocore.exceptions import ClientError
from catch_models import CatchPaths
from click.testing import CliRunner
from pythonjsonlogger.json import JsonFormatter
from testing.conftest import TEST_BUCKET

from app import main


def test_cli_ingest_schedule_uploads_raw_json_and_logs(
    monkeypatch: pytest.MonkeyPatch,
    sample_schedule: dict,
    caplog: pytest.LogCaptureFixture,
):
    """The CLI should fetch a schedule, upload it, and log the upload metadata."""
    fake_mlb_client = MagicMock()
    fake_mlb_client.get_schedule.return_value = sample_schedule
    fake_s3_client = MagicMock()
    runner = CliRunner()

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    caplog.set_level(logging.INFO, logger="app.main")

    result = runner.invoke(
        main.cli,
        ["ingest-schedule", "--year", "2025", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 0
    fake_mlb_client.get_schedule.assert_called_once_with(2025)
    fake_s3_client.put_object.assert_called_once()

    kwargs = fake_s3_client.put_object.call_args.kwargs
    assert kwargs["Bucket"] == TEST_BUCKET
    assert kwargs["Key"] == CatchPaths.bronze_schedule_key(2025)
    assert kwargs["ContentType"] == "application/json"
    assert json.loads(kwargs["Body"].decode("utf-8")) == sample_schedule
    assert CatchPaths.bronze_schedule_key(2025) in caplog.text
    assert "file_size=" in caplog.text
    assert "games=6" in caplog.text


def test_cli_ingest_schedule_defaults_to_current_year(
    monkeypatch: pytest.MonkeyPatch,
    sample_schedule: dict,
):
    """Omitting --year should use the current calendar year."""

    class _FakeDate:
        @staticmethod
        def today() -> date:
            return date(2027, 1, 2)

    fake_mlb_client = MagicMock()
    fake_mlb_client.get_schedule.return_value = sample_schedule
    runner = CliRunner()

    monkeypatch.setattr(main, "date", _FakeDate)
    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: MagicMock())

    result = runner.invoke(
        main.cli,
        ["ingest-schedule", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 0
    fake_mlb_client.get_schedule.assert_called_once_with(2027)


def test_cli_ingest_schedule_exits_non_zero_on_api_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """API failures should raise a Click error and skip S3 uploads."""
    fake_mlb_client = MagicMock()
    fake_mlb_client.get_schedule.side_effect = requests.HTTPError("boom")
    fake_s3_client = MagicMock()
    runner = CliRunner()

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    caplog.set_level(logging.INFO, logger="app.main")

    result = runner.invoke(
        main.cli,
        ["ingest-schedule", "--year", "2025", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code != 0
    assert "Failed to fetch schedule for year=2025" in result.output
    assert "Failed to fetch schedule for year=2025" in caplog.text
    fake_s3_client.put_object.assert_not_called()


@pytest.mark.integration
def test_upload_schedule_to_s3_writes_json_object(
    mock_s3_client,
    sample_schedule: dict,
):
    """Moto-backed S3 uploads should persist the schedule JSON with metadata."""
    key, file_size, game_count = main.upload_schedule_to_s3(
        mock_s3_client,
        TEST_BUCKET,
        2025,
        sample_schedule,
    )

    response = mock_s3_client.get_object(Bucket=TEST_BUCKET, Key=key)

    assert key == CatchPaths.bronze_schedule_key(2025)
    assert file_size > 0
    assert game_count == sample_schedule["totalGames"]
    assert response["ContentType"] == "application/json"
    assert json.loads(response["Body"].read().decode("utf-8")) == sample_schedule


def test_shared_schedule_fixture_is_available(sample_schedule):
    """Verify shared schedule fixtures can be reused from the testing dir."""
    assert sample_schedule["totalGames"] >= 5


def _build_schedule_payload(*, schedule_date: str, games: list[dict]) -> dict:
    """Build a minimal schedule payload for one official date."""
    return {
        "dates": [
            {
                "date": schedule_date,
                "games": games,
            }
        ]
    }


def _build_schedule_game(game_pk: int, detailed_state: str = "Final") -> dict:
    """Build a minimal raw schedule game payload."""
    return {
        "gamePk": game_pk,
        "status": {
            "abstractGameState": detailed_state,
            "detailedState": detailed_state,
        },
    }


def _missing_s3_key_error(key: str) -> ClientError:
    """Build an S3-style missing object error for tests."""
    return ClientError(
        {
            "Error": {
                "Code": "404",
                "Message": f"{key} does not exist",
            }
        },
        "HeadObject",
    )


def _mock_schedule_read(fake_s3_client: MagicMock, schedule_payload: dict):
    """Configure a fake S3 client to return a schedule payload."""
    fake_s3_client.get_object.return_value = {
        "Body": BytesIO(json.dumps(schedule_payload).encode("utf-8"))
    }


def _raise_missing_head_object(**kwargs):
    """Raise a missing-object error for a fake S3 HEAD request."""
    raise _missing_s3_key_error(kwargs["Key"])


def test_completed_game_pks_for_date_filters_to_final_games():
    """Only final games for the requested date should be returned."""
    schedule_payload = {
        "dates": [
            {
                "date": "2025-06-15",
                "games": [
                    _build_schedule_game(752400),
                    _build_schedule_game(752401),
                    _build_schedule_game(752402, detailed_state="Postponed"),
                ],
            },
            {
                "date": "2025-06-16",
                "games": [_build_schedule_game(752500)],
            },
        ]
    }

    game_pks = main.completed_game_pks_for_date(
        schedule_payload,
        date(2025, 6, 15),
    )

    assert game_pks == [752400, 752401]


def test_default_target_date_returns_yesterday(monkeypatch: pytest.MonkeyPatch):
    """The default target date should be yesterday."""

    class _FakeDate:
        @staticmethod
        def today() -> date:
            return date(2027, 1, 2)

    monkeypatch.setattr(main, "date", _FakeDate)

    assert main.default_target_date() == date(2027, 1, 1)


def test_parse_target_date_rejects_invalid_values():
    """Invalid date strings should raise a Click bad-parameter error."""
    with pytest.raises(click.BadParameter, match="Use YYYY-MM-DD format"):
        main.parse_target_date("2025-13-45")


def test_configure_logging_updates_existing_handler_formatter(monkeypatch):
    """Text logging should refresh existing handler formatters."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))

    try:
        root_logger.handlers = [handler]
        monkeypatch.delenv("LOG_FORMAT", raising=False)

        main.configure_logging()

        assert handler.formatter is not None
        assert handler.formatter._fmt == "%(levelname)s:%(name)s:%(message)s"
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def test_configure_logging_forces_json_formatter_on_existing_handler(monkeypatch):
    """JSON logging should override handlers even without existing formatters."""
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    handler = logging.StreamHandler()

    try:
        root_logger.handlers = [handler]
        monkeypatch.setenv("LOG_FORMAT", "json")

        main.configure_logging()

        assert isinstance(handler.formatter, JsonFormatter)
    finally:
        root_logger.handlers = original_handlers
        root_logger.setLevel(original_level)


def test_api_call_warning_threshold_invalid_value_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    """Invalid threshold values should warn and fall back to the default."""
    monkeypatch.setenv("API_CALL_WARNING_THRESHOLD", "not-a-number")
    caplog.set_level(logging.WARNING, logger="app.main")

    assert main.api_call_warning_threshold() == main.DEFAULT_API_CALL_WARNING_THRESHOLD
    assert "Invalid API_CALL_WARNING_THRESHOLD; using default" in caplog.text


def test_read_json_from_s3_decodes_body():
    """The S3 helper should decode JSON bytes into a Python dict."""
    fake_s3_client = MagicMock()
    fake_s3_client.get_object.return_value = {
        "Body": BytesIO(b'{"ok": true, "count": 2}')
    }

    payload = main.read_json_from_s3(fake_s3_client, TEST_BUCKET, "bronze/test.json")

    assert payload == {"ok": True, "count": 2}
    assert fake_s3_client.get_object.call_args.kwargs == {
        "Bucket": TEST_BUCKET,
        "Key": "bronze/test.json",
    }


def test_s3_key_exists_reraises_non_missing_errors():
    """Unexpected S3 HEAD errors should be surfaced."""
    fake_s3_client = MagicMock()
    fake_s3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "boom"}},
        "HeadObject",
    )

    with pytest.raises(ClientError, match="boom"):
        main.s3_key_exists(fake_s3_client, TEST_BUCKET, "bronze/test.json")


def test_upload_json_to_s3_writes_json_bytes():
    """Raw JSON uploads should be written with an application/json content type."""
    fake_s3_client = MagicMock()

    file_size = main.upload_json_to_s3(
        fake_s3_client,
        TEST_BUCKET,
        "bronze/test.json",
        {"gamePk": 752400},
    )

    assert file_size > 0
    assert fake_s3_client.put_object.call_args.kwargs == {
        "Bucket": TEST_BUCKET,
        "Key": "bronze/test.json",
        "Body": b'{"gamePk": 752400}',
        "ContentType": "application/json",
    }


@pytest.mark.parametrize(
    ("schedule_game", "expected"),
    [
        (_build_schedule_game(752400), True),
        (
            {
                "gamePk": 752401,
                "status": {
                    "abstractGameState": "Live",
                    "detailedState": "Final",
                },
            },
            True,
        ),
        (_build_schedule_game(752402, detailed_state="Postponed"), False),
        ({"gamePk": 752403}, False),
        ({"gamePk": 752404, "status": "Final"}, False),
    ],
)
def test_is_final_game(schedule_game: dict, expected: bool):
    """The final-game helper should only accept valid Final status payloads."""
    assert main.is_final_game(schedule_game) is expected


def test_cli_ingest_games_uploads_missing_objects_and_skips_existing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
):
    """The CLI should upload missing game JSON and skip fully ingested games."""
    fake_mlb_client = MagicMock()
    fake_mlb_client.get_boxscore.side_effect = lambda game_pk: {
        "gamePk": game_pk,
        "endpoint": "boxscore",
    }
    fake_mlb_client.get_content.side_effect = lambda game_pk: {
        "gamePk": game_pk,
        "endpoint": "content",
    }
    fake_s3_client = MagicMock()
    runner = CliRunner()
    schedule_payload = _build_schedule_payload(
        schedule_date="2025-06-15",
        games=[
            _build_schedule_game(752400),
            _build_schedule_game(752401),
            _build_schedule_game(752402, detailed_state="Postponed"),
        ],
    )
    existing_keys = {
        CatchPaths.bronze_boxscore_key(752401),
        CatchPaths.bronze_content_key(752401),
    }

    def _head_object(*, Bucket: str, Key: str):
        assert Bucket == TEST_BUCKET
        if Key in existing_keys:
            return {}
        raise _missing_s3_key_error(Key)

    _mock_schedule_read(fake_s3_client, schedule_payload)
    fake_s3_client.head_object.side_effect = _head_object

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO, logger="app.main")

    result = runner.invoke(
        main.cli,
        ["ingest-games", "--date", "2025-06-15", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 0
    assert fake_s3_client.get_object.call_args.kwargs == {
        "Bucket": TEST_BUCKET,
        "Key": CatchPaths.bronze_schedule_key(2025),
    }
    fake_mlb_client.get_boxscore.assert_called_once_with(752400)
    fake_mlb_client.get_content.assert_called_once_with(752400)

    uploaded_keys = [
        call.kwargs["Key"] for call in fake_s3_client.put_object.call_args_list
    ]
    assert uploaded_keys == [
        CatchPaths.bronze_boxscore_key(752400),
        CatchPaths.bronze_content_key(752400),
    ]

    summary = json.loads(result.output)
    assert summary == {
        "bucket": TEST_BUCKET,
        "correlation_id": "2025-06-15",
        "date": "2025-06-15",
        "dry_run": False,
        "failed_game_pks": [],
        "failed_games_file": "failed_games.json",
        "games_failed": 0,
        "games_found": 2,
        "games_processed": 1,
        "games_skipped": 1,
        "games_succeeded": 1,
        "games_to_process": 1,
        "games_uploaded": 1,
        "boxscores_uploaded": 1,
        "contents_uploaded": 1,
        "schedule_key": CatchPaths.bronze_schedule_key(2025),
    }
    assert json.loads(Path("failed_games.json").read_text(encoding="utf-8")) == []
    assert any(
        record.message == "Ingestion run summary"
        and record.games_processed == 1
        and record.games_skipped == 1
        and record.games_succeeded == 1
        for record in caplog.records
    )


def test_cli_ingest_games_defaults_to_yesterday(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Omitting --date should ingest yesterday's completed games."""

    class _FakeDate:
        @staticmethod
        def today() -> date:
            return date(2027, 1, 2)

        @staticmethod
        def fromisoformat(value: str) -> date:
            return date.fromisoformat(value)

    fake_s3_client = MagicMock()
    _mock_schedule_read(
        fake_s3_client,
        _build_schedule_payload(schedule_date="2027-01-01", games=[]),
    )
    runner = CliRunner()

    monkeypatch.setattr(main, "date", _FakeDate)
    monkeypatch.setattr(main, "create_mlb_client", lambda: MagicMock())
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        main.cli,
        ["ingest-games", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 0
    summary = json.loads(result.output)
    assert summary["date"] == "2027-01-01"
    assert summary["schedule_key"] == CatchPaths.bronze_schedule_key(2027)


def test_cli_ingest_games_handles_content_404_as_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
):
    """Content 404s should warn and continue without failing the command."""
    fake_mlb_client = MagicMock()
    fake_mlb_client.get_boxscore.return_value = {"gamePk": 752400}
    response = requests.Response()
    response.status_code = 404
    response.url = "/api/v1/game/752400/content"
    fake_mlb_client.get_content.side_effect = requests.HTTPError(response=response)
    fake_s3_client = MagicMock()
    runner = CliRunner()

    _mock_schedule_read(
        fake_s3_client,
        _build_schedule_payload(
            schedule_date="2025-06-15",
            games=[_build_schedule_game(752400)],
        ),
    )
    fake_s3_client.head_object.side_effect = _raise_missing_head_object

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO, logger="app.main")

    result = runner.invoke(
        main.cli,
        ["ingest-games", "--date", "2025-06-15", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 0
    uploaded_keys = [
        call.kwargs["Key"] for call in fake_s3_client.put_object.call_args_list
    ]
    assert uploaded_keys == [CatchPaths.bronze_boxscore_key(752400)]

    summary = json.loads(result.output)
    assert summary["games_failed"] == 0
    assert summary["games_succeeded"] == 1
    assert summary["boxscores_uploaded"] == 1
    assert summary["contents_uploaded"] == 0
    assert "Content not found for game; skipping content upload" in caplog.text


def test_cli_ingest_games_continues_after_boxscore_error_and_uploads_content(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
):
    """A boxscore failure should still allow content upload and later games."""
    fake_mlb_client = MagicMock()
    fake_s3_client = MagicMock()
    runner = CliRunner()

    def _get_boxscore(game_pk: int) -> dict:
        if game_pk == 752400:
            raise requests.Timeout("boom")
        return {"gamePk": game_pk, "endpoint": "boxscore"}

    fake_mlb_client.get_boxscore.side_effect = _get_boxscore
    fake_mlb_client.get_content.side_effect = lambda game_pk: {
        "gamePk": game_pk,
        "endpoint": "content",
    }

    _mock_schedule_read(
        fake_s3_client,
        _build_schedule_payload(
            schedule_date="2025-06-15",
            games=[_build_schedule_game(752400), _build_schedule_game(752401)],
        ),
    )
    fake_s3_client.head_object.side_effect = _raise_missing_head_object

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO, logger="app.main")

    result = runner.invoke(
        main.cli,
        ["ingest-games", "--date", "2025-06-15", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 1
    uploaded_keys = [
        call.kwargs["Key"] for call in fake_s3_client.put_object.call_args_list
    ]
    assert CatchPaths.bronze_content_key(752400) in uploaded_keys
    assert CatchPaths.bronze_boxscore_key(752401) in uploaded_keys
    assert CatchPaths.bronze_content_key(752401) in uploaded_keys

    summary = json.loads(result.output)
    assert summary["games_found"] == 2
    assert summary["games_processed"] == 2
    assert summary["games_succeeded"] == 1
    assert summary["games_failed"] == 1
    assert summary["failed_game_pks"] == [752400]
    assert json.loads(Path("failed_games.json").read_text(encoding="utf-8")) == [752400]
    assert any(
        record.message == "Failed to ingest game"
        and record.gamePk == 752400
        and record.error_type == "Timeout"
        and record.attempt_count == 1
        for record in caplog.records
    )


def test_cli_ingest_games_supports_dry_run(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
):
    """Dry-run mode should avoid API calls and S3 writes."""
    fake_mlb_client = MagicMock()
    fake_s3_client = MagicMock()
    runner = CliRunner()

    _mock_schedule_read(
        fake_s3_client,
        _build_schedule_payload(
            schedule_date="2025-06-15",
            games=[_build_schedule_game(752400)],
        ),
    )
    fake_s3_client.head_object.side_effect = _raise_missing_head_object

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO, logger="app.main")

    result = runner.invoke(
        main.cli,
        [
            "ingest-games",
            "--date",
            "2025-06-15",
            "--bucket",
            TEST_BUCKET,
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    fake_mlb_client.get_boxscore.assert_not_called()
    fake_mlb_client.get_content.assert_not_called()
    fake_s3_client.put_object.assert_not_called()

    summary = json.loads(result.output)
    assert summary["dry_run"] is True
    assert summary["games_processed"] == 1
    assert summary["games_failed"] == 0
    assert "Dry run would fetch and upload boxscore" in caplog.text
    assert "Dry run would fetch and upload content" in caplog.text


def test_cli_ingest_games_returns_total_failure_exit_code_when_all_games_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    """Runs where every processed game fails should exit with code 2."""
    fake_mlb_client = MagicMock()
    fake_s3_client = MagicMock()
    runner = CliRunner()

    fake_mlb_client.get_boxscore.side_effect = requests.ConnectionError("boom")
    fake_mlb_client.get_content.side_effect = requests.ConnectionError("boom")

    _mock_schedule_read(
        fake_s3_client,
        _build_schedule_payload(
            schedule_date="2025-06-15",
            games=[_build_schedule_game(752400)],
        ),
    )
    fake_s3_client.head_object.side_effect = _raise_missing_head_object

    monkeypatch.setattr(main, "create_mlb_client", lambda: fake_mlb_client)
    monkeypatch.setattr(main, "create_s3_client", lambda: fake_s3_client)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        main.cli,
        ["ingest-games", "--date", "2025-06-15", "--bucket", TEST_BUCKET],
    )

    assert result.exit_code == 2
    summary = json.loads(result.output)
    assert summary["games_processed"] == 1
    assert summary["games_succeeded"] == 0
    assert summary["games_failed"] == 1
