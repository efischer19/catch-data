"""Shared data models and S3 path conventions for the medallion architecture.

See ADR-018 (Medallion Architecture) for pattern context.
"""

from catch_models.models import BronzeRecord, GoldMetric, SilverEntity
from catch_models.s3_paths import MedallionPaths

__all__ = ["BronzeRecord", "GoldMetric", "MedallionPaths", "SilverEntity"]
