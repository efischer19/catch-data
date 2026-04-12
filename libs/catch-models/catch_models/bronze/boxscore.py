"""Pydantic models for the MLB Stats API live-feed / boxscore endpoint.

Endpoint: ``/api/v1.1/game/{game_pk}/feed/live``

The live-feed response is very large.  These models capture the
top-level envelope and the most important nested structures
(gameData, liveData with linescore and boxscore).  Deeply nested
player-level statistics are typed as plain ``dict`` to keep the
model maintainable while still catching top-level drift.

See ADR-018 (Medallion Architecture) for the Bronze layer's role.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

_BRONZE_CONFIG = ConfigDict(strict=True, extra="forbid")


# -- Metadata --------------------------------------------------------------
class _MetaData(BaseModel):
    model_config = _BRONZE_CONFIG

    wait: int | None = None
    timeStamp: str | None = None
    gameEvents: list[str] | None = None
    logicalEvents: list[str] | None = None


# -- gameData nested models ------------------------------------------------
class _GameInfo(BaseModel):
    model_config = _BRONZE_CONFIG

    pk: int
    type: str
    doubleHeader: str
    id: str
    gamedayType: str
    tiebreaker: str
    gameNumber: int
    calendarEventID: str
    season: str
    seasonDisplay: str


class _DatetimeInfo(BaseModel):
    model_config = _BRONZE_CONFIG

    dateTime: str | None = None
    originalDate: str | None = None
    officialDate: str | None = None
    dayNight: str | None = None
    time: str | None = None
    ampm: str | None = None


class _GameDataStatus(BaseModel):
    model_config = _BRONZE_CONFIG

    abstractGameState: str
    codedGameState: str
    detailedState: str
    statusCode: str
    startTimeTBD: bool
    abstractGameCode: str
    reason: str | None = None


class _TeamRef(BaseModel):
    model_config = _BRONZE_CONFIG

    id: int
    name: str
    link: str


class _TeamRecord(BaseModel):
    model_config = _BRONZE_CONFIG

    gamesPlayed: int | None = None
    wins: int | None = None
    losses: int | None = None
    winningPercentage: str | None = None


class _TeamFull(BaseModel):
    model_config = _BRONZE_CONFIG

    id: int
    name: str
    link: str
    abbreviation: str | None = None
    teamName: str | None = None
    shortName: str | None = None
    record: _TeamRecord | None = None


class _GameDataTeams(BaseModel):
    model_config = _BRONZE_CONFIG

    away: _TeamFull
    home: _TeamFull


class _VenueInfo(BaseModel):
    model_config = _BRONZE_CONFIG

    id: int
    name: str
    link: str


class _GameData(BaseModel):
    """``gameData`` section of the live-feed response."""

    model_config = _BRONZE_CONFIG

    game: _GameInfo
    datetime: _DatetimeInfo
    status: _GameDataStatus
    teams: _GameDataTeams
    venue: _VenueInfo
    players: dict[str, object] | None = None  # deeply nested per-player data


# -- liveData nested models ------------------------------------------------
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


class _BoxscoreTeamEntry(BaseModel):
    """One side (away or home) inside liveData.boxscore.teams."""

    model_config = _BRONZE_CONFIG

    team: _TeamRef
    teamStats: dict[str, object]  # deeply nested batting/pitching aggregates
    players: dict[str, object]  # deeply nested per-player stat lines
    batters: list[int]
    pitchers: list[int]
    bench: list[int]
    bullpen: list[int]
    battingOrder: list[int]
    info: list[dict[str, object]]
    note: list[object] | None = None


class _BoxscoreTeams(BaseModel):
    model_config = _BRONZE_CONFIG

    away: _BoxscoreTeamEntry
    home: _BoxscoreTeamEntry


class _Official(BaseModel):
    model_config = _BRONZE_CONFIG

    official: _TeamRef
    officialType: str


class _Boxscore(BaseModel):
    model_config = _BRONZE_CONFIG

    teams: _BoxscoreTeams
    officials: list[_Official]


class _DecisionPitcher(BaseModel):
    model_config = _BRONZE_CONFIG

    id: int
    fullName: str
    link: str


class _Decisions(BaseModel):
    model_config = _BRONZE_CONFIG

    winner: _DecisionPitcher | None = None
    loser: _DecisionPitcher | None = None
    save: _DecisionPitcher | None = None


class _LiveData(BaseModel):
    """``liveData`` section of the live-feed response."""

    model_config = _BRONZE_CONFIG

    plays: dict[str, object] | None = None  # deeply nested play-by-play data
    linescore: _Linescore
    boxscore: _Boxscore
    decisions: _Decisions | None = None


# -- Top-level response ----------------------------------------------------
class BoxscoreResponse(BaseModel):
    """Full response from the live-feed (boxscore) endpoint.

    Usage::

        data = BoxscoreResponse.model_validate_json(raw_bytes)
    """

    model_config = _BRONZE_CONFIG

    copyright: str
    gamePk: int
    link: str
    metaData: _MetaData | None = None
    gameData: _GameData
    liveData: _LiveData
