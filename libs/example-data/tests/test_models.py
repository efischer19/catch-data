"""Tests for the medallion architecture data models."""

from datetime import datetime

from example_data.models import BronzeRecord, GoldMetric, SilverEntity


def test_bronze_record_defaults():
    """Verify BronzeRecord populates default fields."""
    record = BronzeRecord(source="test-source")
    assert record.source == "test-source"
    assert isinstance(record.ingested_at, datetime)
    assert record.raw_data == {}


def test_bronze_record_with_raw_data():
    """Verify BronzeRecord accepts arbitrary raw data."""
    record = BronzeRecord(
        source="api",
        raw_data={"key": "value", "count": 42},
    )
    assert record.raw_data == {"key": "value", "count": 42}


def test_silver_entity_required_fields():
    """Verify SilverEntity requires entity_id and name."""
    entity = SilverEntity(entity_id="usr-001", name="Test User")
    assert entity.entity_id == "usr-001"
    assert entity.name == "Test User"
    assert isinstance(entity.processed_at, datetime)


def test_gold_metric_required_fields():
    """Verify GoldMetric requires metric_name and value."""
    metric = GoldMetric(metric_name="daily-active-users", value=1234.5)
    assert metric.metric_name == "daily-active-users"
    assert metric.value == 1234.5
    assert metric.dimensions == {}
    assert isinstance(metric.computed_at, datetime)


def test_gold_metric_with_dimensions():
    """Verify GoldMetric accepts dimension keys."""
    metric = GoldMetric(
        metric_name="revenue",
        value=99999.99,
        dimensions={"region": "us-east-1", "category": "premium"},
    )
    assert metric.dimensions["region"] == "us-east-1"
