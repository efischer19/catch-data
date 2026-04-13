"""S3 key conventions for the catch-data medallion architecture.

Key layout::

    s3://{bucket}/
    ├── bronze/schedule_{year}.json
    ├── bronze/boxscore_{game_pk}.json
    ├── bronze/content_{game_pk}.json
    ├── silver/master_schedule_{year}.json
    ├── gold/team_{team_id}.json
    └── gold/upcoming_games.json

See ADR-018 (Medallion Architecture) for the broader pipeline context.
"""

from datetime import date


class CatchPaths:
    """Generate deterministic S3 object keys for catch-data pipeline outputs."""

    @staticmethod
    def bronze_schedule_key(year: int) -> str:
        """Return the bronze schedule object key for a season year."""
        return f"bronze/schedule_{year}.json"

    @staticmethod
    def bronze_boxscore_key(game_pk: int) -> str:
        """Return the bronze boxscore object key for a single game."""
        return f"bronze/boxscore_{game_pk}.json"

    @staticmethod
    def bronze_content_key(game_pk: int) -> str:
        """Return the bronze content object key for a single game."""
        return f"bronze/content_{game_pk}.json"

    @staticmethod
    def silver_master_schedule_key(year: int) -> str:
        """Return the silver master schedule object key for a season year."""
        return f"silver/master_schedule_{year}.json"

    @staticmethod
    def gold_team_key(team_id: int) -> str:
        """Return the gold team schedule object key for a team."""
        return f"gold/team_{team_id}.json"

    @staticmethod
    def gold_upcoming_games_key() -> str:
        """Return the gold upcoming games object key."""
        return "gold/upcoming_games.json"


class MedallionPaths:
    """Legacy template helper for generic medallion key prefixes."""

    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name

    def bronze(self, source: str, processing_date: date) -> str:
        """Return the legacy bronze key prefix."""
        return f"bronze/{source}/{processing_date.isoformat()}/"

    def silver(self, entity: str, processing_date: date) -> str:
        """Return the legacy silver key prefix."""
        return f"silver/{entity}/{processing_date.isoformat()}/"

    def gold(self, metric_name: str) -> str:
        """Return the legacy gold key prefix."""
        return f"gold/served/{metric_name}/"

    def s3_uri(self, key_prefix: str) -> str:
        """Return the full ``s3://`` URI for a given key prefix."""
        return f"s3://{self.bucket_name}/{key_prefix}"
