"""S3 key path conventions for the medallion architecture.

This module defines the standard S3 key prefix layout used by the
data pipeline. All pipeline stages should use these conventions to
ensure consistent, discoverable data organization.

Key layout::

    s3://{{S3_BUCKET_NAME}}/
    ├── bronze/{source}/{YYYY-MM-DD}/       # Raw ingested data
    ├── silver/{entity}/{YYYY-MM-DD}/       # Cleaned & validated data
    └── gold/served/{metric_name}/          # Business-ready aggregations

See ADR-018 (Medallion Architecture) for pattern context.
"""

from datetime import date


class MedallionPaths:
    """Generate S3 key prefixes for each medallion layer.

    Parameters
    ----------
    bucket_name : str
        The S3 bucket name (or use the ``S3_BUCKET_NAME`` environment
        variable at runtime).

    Examples
    --------
    >>> paths = MedallionPaths("my-project-data-dev")
    >>> paths.bronze("api-source", date(2026, 1, 15))
    'bronze/api-source/2026-01-15/'
    >>> paths.silver("users", date(2026, 1, 15))
    'silver/users/2026-01-15/'
    >>> paths.gold("daily-active-users")
    'gold/served/daily-active-users/'
    """

    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name

    def bronze(self, source: str, processing_date: date) -> str:
        """Return the S3 key prefix for bronze (raw) data.

        Parameters
        ----------
        source : str
            Name of the data source (e.g., ``"api-source"``).
        processing_date : date
            The date partition for the data.

        Returns
        -------
        str
            S3 key prefix, e.g. ``"bronze/api-source/2026-01-15/"``.
        """
        return f"bronze/{source}/{processing_date.isoformat()}/"

    def silver(self, entity: str, processing_date: date) -> str:
        """Return the S3 key prefix for silver (cleaned) data.

        Parameters
        ----------
        entity : str
            Name of the entity type (e.g., ``"users"``).
        processing_date : date
            The date partition for the data.

        Returns
        -------
        str
            S3 key prefix, e.g. ``"silver/users/2026-01-15/"``.
        """
        return f"silver/{entity}/{processing_date.isoformat()}/"

    def gold(self, metric_name: str) -> str:
        """Return the S3 key prefix for gold (served) data.

        Parameters
        ----------
        metric_name : str
            Name of the metric or dataset being served.

        Returns
        -------
        str
            S3 key prefix, e.g. ``"gold/served/daily-active-users/"``.
        """
        return f"gold/served/{metric_name}/"

    def s3_uri(self, key_prefix: str) -> str:
        """Return the full ``s3://`` URI for a given key prefix.

        Parameters
        ----------
        key_prefix : str
            The S3 key prefix (e.g., from :meth:`bronze`).

        Returns
        -------
        str
            Full S3 URI, e.g.
            ``"s3://my-bucket/bronze/api-source/2026-01-15/"``.
        """
        return f"s3://{self.bucket_name}/{key_prefix}"
