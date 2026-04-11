"""Tests for the example-analytics (Gold layer) CLI."""

from click.testing import CliRunner

from app.main import cli, compute_metrics, read_from_s3, write_to_s3


def test_cli_aggregate_runs():
    """Verify the aggregate command runs without error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "aggregate",
            "--entity",
            "items",
            "--metric-name",
            "test-metrics",
            "--date",
            "2026-01-15",
        ],
    )
    assert result.exit_code == 0
    assert "Reading silver data" in result.output
    assert "Wrote" in result.output


def test_read_from_s3_returns_list():
    """Verify the placeholder read returns a list of dicts."""
    records = read_from_s3("silver/items/2026-01-15/")
    assert isinstance(records, list)
    assert len(records) > 0


def test_compute_metrics_counts():
    """Verify compute_metrics groups and counts records."""
    records = [
        {"entity_id": "1", "name": "a"},
        {"entity_id": "2", "name": "b"},
        {"entity_id": "3", "name": "a"},
    ]
    metrics = compute_metrics(records)
    assert isinstance(metrics, list)
    assert len(metrics) == 2

    by_name = {m["dimensions"]["name"]: m["value"] for m in metrics}
    assert by_name["a"] == 2.0
    assert by_name["b"] == 1.0


def test_compute_metrics_empty_input():
    """Verify compute_metrics handles empty input."""
    metrics = compute_metrics([])
    assert metrics == []


def test_write_to_s3_returns_count():
    """Verify the placeholder write returns the record count."""
    records = [{"metric_name": "test", "value": 1.0}]
    count = write_to_s3(records, "gold/served/test-metrics/")
    assert count == 1
