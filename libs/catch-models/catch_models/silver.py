"""Pydantic models for Silver-layer cleaned MLB game data."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

_SILVER_CONFIG = ConfigDict(
    extra="forbid",
    populate_by_name=True,
    serialize_by_alias=True,
)


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _serialize_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class DataCompleteness(StrEnum):
    """Completeness state for a Silver-layer game record."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class _SilverBaseModel(BaseModel):
    model_config = _SILVER_CONFIG

    @field_validator(
        "date",
        "last_updated",
        "source_updated_at",
        mode="after",
        check_fields=False,
    )
    @classmethod
    def _validate_utc_timestamps(cls, value: datetime) -> datetime:
        return _normalize_utc(value)

    @field_serializer(
        "date",
        "last_updated",
        "source_updated_at",
        when_used="json",
        check_fields=False,
    )
    def _serialize_timestamps(self, value: datetime) -> str:
        return _serialize_utc(value)


class SilverGame(_SilverBaseModel):
    """Cleaned, flattened Silver-layer representation of one MLB game."""

    game_pk: int = Field(..., alias="gamePk", description="Unique MLB game identifier")
    date: datetime = Field(..., description="Scheduled first-pitch timestamp in UTC")
    game_type: str = Field(..., description="MLB game type code such as R, S, or A")
    game_number: int = Field(1, ge=1, description="Doubleheader game number")
    doubleheader_type: Literal["N", "Y", "S"] = Field(
        "N",
        description="Doubleheader type: N none, Y traditional, S split",
    )
    away_team_id: int
    away_team_name: str
    away_team_abbreviation: str
    home_team_id: int
    home_team_name: str
    home_team_abbreviation: str
    venue_id: int
    venue_name: str
    status: str = Field(..., description="Primary game status")
    status_detail: str = Field(..., description="Detailed game status")
    current_inning: int | None = Field(None, ge=1, description="Current inning, if any")
    inning_state: str | None = Field(None, description="Top, Bottom, Middle, End, etc.")
    innings: int | None = Field(
        None,
        ge=1,
        description="Completed or scheduled inning count for the game",
    )
    away_runs: int | None = None
    away_hits: int | None = None
    away_errors: int | None = None
    home_runs: int | None = None
    home_hits: int | None = None
    home_errors: int | None = None
    winning_pitcher_name: str | None = None
    losing_pitcher_name: str | None = None
    save_pitcher_name: str | None = None
    condensed_game_url: AnyHttpUrl | None = Field(
        None,
        description="Condensed game highlight video URL, if available",
    )
    source_updated_at: datetime = Field(
        ...,
        description="Timestamp when Bronze-layer source data was last refreshed",
    )
    data_completeness: DataCompleteness = Field(
        ...,
        description="Whether boxscore data is full, partial, or absent",
    )


class SilverProcessingErrors(BaseModel):
    """Summary of Silver-layer records excluded during processing."""

    model_config = _SILVER_CONFIG

    count: int = Field(0, ge=0, description="Number of games excluded from output")
    game_pks: list[int] = Field(
        default_factory=list,
        alias="gamePks",
        description="MLB game identifiers excluded during processing",
    )

    @model_validator(mode="after")
    def _validate_count_matches_games(self) -> SilverProcessingErrors:
        if self.count != len(self.game_pks):
            raise ValueError("processing error count must match the number of gamePks")
        return self


class SilverMasterSchedule(_SilverBaseModel):
    """Season container for Silver-layer MLB game records."""

    year: int = Field(..., ge=1876, description="Season year")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the master schedule was last generated",
    )
    games: list[SilverGame] = Field(
        default_factory=list,
        description="Silver-layer game records for the season",
    )
    processing_errors: SilverProcessingErrors = Field(
        default_factory=SilverProcessingErrors,
        description="Summary of games excluded from the Silver output",
    )
