"""Tests for the S3 path convention utilities."""

from datetime import date

from example_data.s3_paths import MedallionPaths


def test_bronze_path():
    """Verify bronze path follows the convention."""
    paths = MedallionPaths("my-bucket")
    result = paths.bronze("api-source", date(2026, 1, 15))
    assert result == "bronze/api-source/2026-01-15/"


def test_silver_path():
    """Verify silver path follows the convention."""
    paths = MedallionPaths("my-bucket")
    result = paths.silver("users", date(2026, 3, 20))
    assert result == "silver/users/2026-03-20/"


def test_gold_path():
    """Verify gold path follows the convention."""
    paths = MedallionPaths("my-bucket")
    result = paths.gold("daily-active-users")
    assert result == "gold/served/daily-active-users/"


def test_s3_uri():
    """Verify full S3 URI construction."""
    paths = MedallionPaths("my-project-data-dev")
    key_prefix = paths.bronze("events", date(2026, 6, 1))
    uri = paths.s3_uri(key_prefix)
    assert uri == "s3://my-project-data-dev/bronze/events/2026-06-01/"
