"""Pydantic model skeletons for medallion architecture data validation.

These models demonstrate the pattern of progressively refining data
through the Bronze → Silver → Gold pipeline layers. Replace or extend
these skeletons with your domain-specific fields.

See ADR-018 (Medallion Architecture) for pattern context.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Bronze Layer — Raw ingested data
# ---------------------------------------------------------------------------
class BronzeRecord(BaseModel):
    """Raw record as ingested from an external source.

    Bronze records preserve the original data with minimal
    transformation. Add metadata fields (source, ingestion timestamp)
    to support lineage tracking.

    Customize this model:
        - Add fields matching your raw data source schema.
        - Keep validation minimal — the goal is to capture data
          faithfully, not to clean it.
    """

    source: str = Field(..., description="Name of the data source")
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the record was ingested",
    )
    raw_data: dict = Field(
        default_factory=dict,
        description="Raw payload from the source (customize per domain)",
    )


# ---------------------------------------------------------------------------
# Silver Layer — Cleaned and validated data
# ---------------------------------------------------------------------------
class SilverEntity(BaseModel):
    """Cleaned, validated entity derived from bronze data.

    Silver records represent data that has been validated, deduplicated,
    and conformed to a consistent schema. This is the layer where
    Pydantic validation shines.

    Customize this model:
        - Replace the placeholder fields with your domain entities.
        - Add strict validation rules (e.g., regex patterns, ranges).
        - Use Pydantic validators for cross-field checks.
    """

    entity_id: str = Field(..., description="Unique identifier for the entity")
    name: str = Field(..., description="Entity name (customize per domain)")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the record was processed",
    )
    # TODO: Add your domain-specific validated fields here.
    # Example:
    #   email: EmailStr = Field(..., description="Validated email address")
    #   category: Literal["A", "B", "C"] = Field(...)


# ---------------------------------------------------------------------------
# Gold Layer — Business-ready aggregated data
# ---------------------------------------------------------------------------
class GoldMetric(BaseModel):
    """Aggregated metric ready for analytics or serving.

    Gold records are the final output of the pipeline — pre-computed
    aggregations, KPIs, or feature vectors optimized for consumption
    by dashboards, APIs, or ML models.

    Customize this model:
        - Replace the placeholder fields with your business metrics.
        - Add computed fields for derived KPIs.
    """

    metric_name: str = Field(..., description="Name of the metric or KPI")
    value: float = Field(..., description="Computed metric value")
    dimensions: dict = Field(
        default_factory=dict,
        description="Dimension keys for slicing (e.g., region, category)",
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the metric was computed",
    )
    # TODO: Add your domain-specific metric fields here.
    # Example:
    #   period_start: date = Field(...)
    #   period_end: date = Field(...)
    #   confidence_interval: float | None = None
