"""Shared data models and S3 path conventions for the medallion architecture.

See ADR-018 (Medallion Architecture) for pattern context.
"""

from example_data.models import BronzeRecord, GoldMetric, SilverEntity
from example_data.s3_paths import MedallionPaths

__all__ = ["BronzeRecord", "GoldMetric", "MedallionPaths", "SilverEntity"]
