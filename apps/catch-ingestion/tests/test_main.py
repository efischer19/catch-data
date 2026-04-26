"""Tests for the catch-ingestion Bronze schedule CLI."""

from __future__ import annotations

import json
import logging
from datetime import date
from unittest.mock import MagicMock

import pytest
import requests
from catch_models import CatchPaths
from click.testing import CliRunner
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
