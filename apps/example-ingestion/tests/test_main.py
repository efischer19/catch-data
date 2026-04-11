"""Tests for the example-ingestion (Bronze layer) CLI."""

from click.testing import CliRunner

from app.main import cli, fetch_from_source, write_to_s3


def test_cli_ingest_runs():
    """Verify the ingest command runs without error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["ingest", "--source", "test", "--date", "2026-01-15"])
    assert result.exit_code == 0
    assert "Ingesting from source=test" in result.output
    assert "Wrote" in result.output


def test_fetch_from_source_returns_list():
    """Verify the placeholder fetch returns a list of dicts."""
    records = fetch_from_source()
    assert isinstance(records, list)
    assert len(records) > 0
    assert isinstance(records[0], dict)


def test_write_to_s3_returns_count():
    """Verify the placeholder write returns the record count."""
    records = [{"id": "1"}, {"id": "2"}]
    count = write_to_s3(records, "bronze/test/2026-01-15/")
    assert count == 2
