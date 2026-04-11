"""Tests for the example-processing (Silver layer) CLI."""

from click.testing import CliRunner

from app.main import cli, read_from_s3, transform_record, write_to_s3


def test_cli_process_runs():
    """Verify the process command runs without error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["process", "--source", "test", "--entity", "items", "--date", "2026-01-15"],
    )
    assert result.exit_code == 0
    assert "Processing bronze data" in result.output
    assert "Wrote" in result.output


def test_read_from_s3_returns_list():
    """Verify the placeholder read returns a list of dicts."""
    records = read_from_s3("bronze/test/2026-01-15/")
    assert isinstance(records, list)
    assert len(records) > 0


def test_transform_record_valid():
    """Verify transform_record extracts expected fields."""
    raw = {"raw_data": {"id": "42", "value": "test-value"}}
    result = transform_record(raw)
    assert result is not None
    assert result["entity_id"] == "42"
    assert result["name"] == "test-value"


def test_transform_record_missing_id():
    """Verify transform_record returns None for records without an id."""
    raw = {"raw_data": {"value": "no-id"}}
    result = transform_record(raw)
    assert result is None


def test_write_to_s3_returns_count():
    """Verify the placeholder write returns the record count."""
    records = [{"entity_id": "1"}, {"entity_id": "2"}]
    count = write_to_s3(records, "silver/items/2026-01-15/")
    assert count == 2
