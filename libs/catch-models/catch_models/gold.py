"""Pydantic models for Gold-layer UI-ready JSON views.

These models define the public API contract for the catch-app frontend.
They are the final output of the medallion pipeline and are served via
CloudFront as static JSON files:

- ``gold/team_{team_id}.json``  → serialised :class:`GoldTeamSchedule`
- ``gold/upcoming_games.json``  → serialised :class:`GoldUpcomingGames`

Design goals
------------
* **Lean** — only fields the frontend currently needs (YAGNI).
* **Small** — short but clear field names to minimise CloudFront payload.
* **Clean** — ``model_dump(mode="json")`` produces self-contained JSON
  with no raw API artefacts or internal pipeline metadata.
* **Schema-friendly** — ``model_json_schema()`` produces a self-contained
  schema suitable for cross-repo consumption (no unresolved ``$ref``
  cycles at the top level).

See ADR-018 (Medallion Architecture) for layer context.
"""

from __future__ import annotations

from datetime import UTC, datetime
from datetime import date as calendar_date

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

_GOLD_CONFIG = ConfigDict(
    extra="forbid",
    populate_by_name=True,
)


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _serialize_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class _GoldBaseModel(BaseModel):
    model_config = _GOLD_CONFIG

    @field_validator("last_updated", mode="after", check_fields=False)
    @classmethod
    def _validate_utc_timestamps(cls, value: datetime) -> datetime:
        return _normalize_utc(value)

    @field_serializer("last_updated", when_used="json", check_fields=False)
    def _serialize_timestamps(self, value: datetime) -> str:
        return _serialize_utc(value)


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class GoldTeamInfo(BaseModel):
    """Lightweight team identity snapshot embedded in each game summary.

    League and division are included so the frontend can filter or group
    games without a separate team-lookup call.
    """

    model_config = _GOLD_CONFIG

    id: int = Field(..., description="MLB team identifier")
    name: str = Field(..., description="Full team name")
    abbreviation: str = Field(..., description="Three-letter team abbreviation")
    league: str = Field(..., description="League name (e.g. American League)")
    division: str = Field(..., description="Division name (e.g. AL East)")


class GoldScore(BaseModel):
    """Run totals for a completed or in-progress game.

    Absent (``None``) for games that have not yet started or are
    postponed.  The pre-formatted :attr:`GoldGameSummary.score_display`
    string is the canonical display value; this model holds the raw
    integers for any arithmetic the frontend may need.
    """

    model_config = _GOLD_CONFIG

    away: int = Field(..., description="Away team runs scored")
    home: int = Field(..., description="Home team runs scored")


class GoldBoxscoreSummary(BaseModel):
    """Full R/H/E line and pitching decisions for a completed game.

    Present only when ``data_completeness`` is ``"full"`` in the Silver
    layer (i.e., the boxscore endpoint returned successfully).  The
    frontend uses this to render the condensed score-line beneath each
    finished game card.

    Field names use the traditional R/H/E abbreviations to keep the
    Gold JSON payload compact.
    """

    model_config = _GOLD_CONFIG

    away_r: int = Field(..., description="Away runs")
    away_h: int = Field(..., description="Away hits")
    away_e: int = Field(..., description="Away errors")
    home_r: int = Field(..., description="Home runs")
    home_h: int = Field(..., description="Home hits")
    home_e: int = Field(..., description="Home errors")
    winning_pitcher: str | None = Field(None, description="Winning pitcher full name")
    losing_pitcher: str | None = Field(None, description="Losing pitcher full name")
    save_pitcher: str | None = Field(None, description="Save pitcher full name, if any")


# ---------------------------------------------------------------------------
# Core game summary
# ---------------------------------------------------------------------------


class GoldGameSummary(BaseModel):
    """Single-game view model consumed by the catch-app frontend.

    This is the atomic unit of both :class:`GoldTeamSchedule` and
    :class:`GoldUpcomingGames`.  Fields are ordered from most- to
    least-frequently accessed to aid human readability of the raw JSON.

    Nullable fields
    ---------------
    * ``score`` / ``score_display`` — absent for pre-game or postponed
    * ``condensed_game_url`` — absent when MLB has not published a clip
    * ``boxscore_summary`` — absent for incomplete or postponed games

    Doubleheader handling
    ---------------------
    Both games share the same calendar date but have distinct
    ``game_pk`` values and a ``game_number`` of 1 or 2.  The frontend
    uses ``game_number`` to render "Game 1" / "Game 2" labels.

    Status values
    -------------
    The frontend must handle at least: ``Final``, ``Postponed``,
    ``Scheduled``, ``In Progress``.  The raw ``status_detail`` string
    from the Silver layer is surfaced here unchanged.
    """

    model_config = _GOLD_CONFIG

    game_pk: int = Field(..., description="Unique MLB game identifier")
    date: datetime = Field(..., description="Scheduled first-pitch timestamp in UTC")
    status: str = Field(
        ...,
        description=("Game status: Final, Postponed, Scheduled, In Progress, etc."),
    )
    game_number: int = Field(
        1,
        ge=1,
        description="Doubleheader game number (1 for single games)",
    )
    venue_name: str = Field(..., description="Venue name for the scheduled game")
    home_team: GoldTeamInfo
    away_team: GoldTeamInfo
    score: GoldScore | None = Field(
        None,
        description="Run totals; null for pre-game or postponed games",
    )
    score_display: str | None = Field(
        None,
        description=(
            "Pre-formatted score string for display (e.g. '3-5');"
            " null when score is null"
        ),
    )
    condensed_game_url: str | None = Field(
        None,
        description="Condensed game highlight video URL; null when not yet available",
    )
    boxscore_summary: GoldBoxscoreSummary | None = Field(
        None,
        description="Full R/H/E line and pitching decisions; null for incomplete games",
    )

    @field_validator("date", mode="after")
    @classmethod
    def _validate_date_utc(cls, value: datetime) -> datetime:
        return _normalize_utc(value)

    @field_serializer("date", when_used="json")
    def _serialize_date(self, value: datetime) -> str:
        return _serialize_utc(value)


# ---------------------------------------------------------------------------
# Top-level view models
# ---------------------------------------------------------------------------


class GoldTeamSchedule(_GoldBaseModel):
    """Full season schedule for a single MLB team.

    Serialised to ``gold/team_{team_id}.json`` and served via CloudFront.
    Contains every game in the season, ordered by date ascending.

    The ``team_id``, ``team_name``, and ``team_abbreviation`` fields at
    the top level are denormalised from :class:`GoldTeamInfo` for
    convenience (the frontend needs them without iterating games).
    """

    team_id: int = Field(..., description="MLB team identifier")
    team_name: str = Field(..., description="Full team name")
    team_abbreviation: str = Field(..., description="Three-letter team abbreviation")
    season_year: int = Field(..., ge=1876, description="MLB season year")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when this file was last generated",
    )
    games: list[GoldGameSummary] = Field(
        default_factory=list,
        description="All season games for the team, ordered by date ascending",
    )


class GoldGameDateGroup(BaseModel):
    """Upcoming-games helper model for frontend-friendly date sections."""

    model_config = _GOLD_CONFIG

    date: calendar_date = Field(
        ...,
        description="UTC calendar date for the grouped games",
    )
    games: list[GoldGameSummary] = Field(
        default_factory=list,
        description="Games on this UTC calendar date, ordered by first pitch ascending",
    )


def _group_games_by_date(games: list[GoldGameSummary]) -> list[GoldGameDateGroup]:
    grouped_games: list[GoldGameDateGroup] = []
    current_date: calendar_date | None = None
    current_games: list[GoldGameSummary] = []

    for game in games:
        game_date = game.date.date()
        if current_date != game_date:
            if current_date is not None:
                grouped_games.append(
                    GoldGameDateGroup(date=current_date, games=current_games)
                )
            current_date = game_date
            current_games = [game]
            continue

        current_games.append(game)

    if current_date is not None:
        grouped_games.append(GoldGameDateGroup(date=current_date, games=current_games))

    return grouped_games


class GoldUpcomingGames(_GoldBaseModel):
    """Consolidated upcoming and recently completed games across all teams.

    Serialised to ``gold/upcoming_games.json`` and served via CloudFront.
    Contains games in a rolling window (yesterday through 7 days out) to
    keep the file size small and data transfer costs low.

    The analytics Lambda determines the rolling window and ordering.  This
    model exposes both the flat ordered game list and a date-grouped view
    so the frontend can render day sections without additional client-side
    reshaping.
    """

    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when this file was last generated",
    )
    games: list[GoldGameSummary] = Field(
        default_factory=list,
        description=(
            "Games in the rolling window (yesterday … +7 days), ordered by date"
        ),
    )
    dates: list[GoldGameDateGroup] = Field(
        default_factory=list,
        description="The same games grouped by UTC calendar date for easy rendering",
    )

    @model_validator(mode="after")
    def _populate_dates_from_games(self) -> GoldUpcomingGames:
        grouped_games = _group_games_by_date(self.games)
        if not self.dates:
            self.dates = grouped_games
            return self

        if self.dates != grouped_games:
            raise ValueError("dates must match the grouped games list")

        return self
