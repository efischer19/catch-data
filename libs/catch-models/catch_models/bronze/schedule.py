"""Pydantic models for the MLB Stats API schedule endpoint response.

Endpoint: ``/api/v1/schedule?sportId=1&season={year}&hydrate=team,venue``

These Bronze-layer models validate and type the raw JSON without
transforming it.  Strict mode is enabled and extra fields are forbidden
so that any upstream API drift is caught immediately.

See ADR-018 (Medallion Architecture) for the Bronze layer's role.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

# -- Shared base for all Bronze models ------------------------------------
_BRONZE_CONFIG = ConfigDict(strict=True, extra="forbid")


# -- Nested helpers --------------------------------------------------------
class _LeagueRecord(BaseModel):
    model_config = _BRONZE_CONFIG

    wins: int
    losses: int
    pct: str


class _TeamRef(BaseModel):
    model_config = _BRONZE_CONFIG

    id: int
    name: str
    link: str


class _TeamEntry(BaseModel):
    model_config = _BRONZE_CONFIG

    leagueRecord: _LeagueRecord
    score: int | None = None
    team: _TeamRef
    isWinner: bool | None = None
    splitSquad: bool
    seriesNumber: int | None = None


class _Teams(BaseModel):
    model_config = _BRONZE_CONFIG

    away: _TeamEntry
    home: _TeamEntry


class _Venue(BaseModel):
    model_config = _BRONZE_CONFIG

    id: int
    name: str
    link: str


class _GameStatus(BaseModel):
    model_config = _BRONZE_CONFIG

    abstractGameState: str
    codedGameState: str
    detailedState: str
    statusCode: str
    startTimeTBD: bool
    abstractGameCode: str
    reason: str | None = None


class _ContentLink(BaseModel):
    model_config = _BRONZE_CONFIG

    link: str


# -- Linescore (hydrated) -------------------------------------------------
class _InningStats(BaseModel):
    """Per-inning run/hit/error tallies for one side (home or away)."""

    model_config = _BRONZE_CONFIG

    runs: int | None = None
    hits: int | None = None
    errors: int | None = None
    leftOnBase: int | None = None


class _LinescoreInning(BaseModel):
    model_config = _BRONZE_CONFIG

    num: int
    ordinalNum: str
    home: _InningStats | None = None
    away: _InningStats | None = None


class _LinescoreTeamStats(BaseModel):
    model_config = _BRONZE_CONFIG

    runs: int | None = None
    hits: int | None = None
    errors: int | None = None
    leftOnBase: int | None = None


class _LinescoreTeams(BaseModel):
    model_config = _BRONZE_CONFIG

    home: _LinescoreTeamStats
    away: _LinescoreTeamStats


class _Linescore(BaseModel):
    model_config = _BRONZE_CONFIG

    currentInning: int | None = None
    currentInningOrdinal: str | None = None
    inningState: str | None = None
    inningHalf: str | None = None
    isTopInning: bool | None = None
    scheduledInnings: int
    innings: list[_LinescoreInning]
    teams: _LinescoreTeams


# -- Game ------------------------------------------------------------------
class ScheduleGame(BaseModel):
    """A single game entry inside a schedule date."""

    model_config = _BRONZE_CONFIG

    gamePk: int
    gameGuid: str
    link: str
    gameType: str
    season: str
    gameDate: str
    officialDate: str
    status: _GameStatus
    teams: _Teams
    venue: _Venue
    content: _ContentLink
    isTie: bool | None = None
    gameNumber: int
    publicFacing: bool
    doubleHeader: str
    gamedayType: str
    tiebreaker: str
    calendarEventID: str
    seasonDisplay: str
    dayNight: str
    scheduledInnings: int
    reverseHomeAwayStatus: bool
    inningBreakLength: int | None = None
    gamesInSeries: int
    seriesGameNumber: int
    seriesDescription: str
    recordSource: str
    ifNecessary: str
    ifNecessaryDescription: str
    linescore: _Linescore | None = None
    description: str | None = None


# -- Date ------------------------------------------------------------------
class ScheduleDate(BaseModel):
    """One calendar date in the schedule response."""

    model_config = _BRONZE_CONFIG

    date: str
    totalItems: int
    totalEvents: int
    totalGames: int
    totalGamesInProgress: int
    games: list[ScheduleGame]
    events: list[object]


# -- Top-level response ----------------------------------------------------
class ScheduleResponse(BaseModel):
    """Full response from the MLB schedule endpoint.

    Usage::

        data = ScheduleResponse.model_validate_json(raw_bytes)
    """

    model_config = _BRONZE_CONFIG

    copyright: str
    totalItems: int
    totalEvents: int
    totalGames: int
    totalGamesInProgress: int
    dates: list[ScheduleDate]
