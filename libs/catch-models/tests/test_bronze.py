"""Tests for Bronze-layer Pydantic models against frozen MLB API fixtures.

Each model is tested with ``model_validate_json()`` against at least two
frozen fixture files — one typical and one edge-case — per the
acceptance criteria in the issue.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from catch_models.bronze.boxscore import BoxscoreResponse
from catch_models.bronze.content import ContentResponse
from catch_models.bronze.schedule import ScheduleResponse

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> bytes:
    """Return raw bytes from a fixture file."""
    return (FIXTURES / name).read_bytes()


# ── Schedule ─────────────────────────────────────────────────────────────


class TestScheduleResponse:
    """Validate ScheduleResponse against frozen fixtures."""

    def test_typical(self):
        resp = ScheduleResponse.model_validate_json(_read("schedule_typical.json"))
        assert resp.totalGames == 2
        assert len(resp.dates) == 2
        game = resp.dates[0].games[0]
        assert game.gamePk == 745678
        assert game.status.detailedState == "Final"
        assert game.doubleHeader == "N"
        assert game.dayNight == "day"

    def test_edge_case_doubleheader(self):
        resp = ScheduleResponse.model_validate_json(
            _read("schedule_edge_case.json"),
        )
        day_games = resp.dates[0].games
        # First two games are a doubleheader
        assert day_games[0].doubleHeader == "Y"
        assert day_games[0].gameNumber == 1
        assert day_games[1].doubleHeader == "Y"
        assert day_games[1].gameNumber == 2

    def test_edge_case_postponed(self):
        resp = ScheduleResponse.model_validate_json(
            _read("schedule_edge_case.json"),
        )
        postponed = resp.dates[0].games[2]
        assert postponed.status.detailedState == "Postponed"
        assert postponed.status.reason == "Rain"
        # Postponed games have no score
        assert postponed.teams.away.score is None
        assert postponed.teams.home.score is None

    def test_edge_case_suspended(self):
        resp = ScheduleResponse.model_validate_json(
            _read("schedule_edge_case.json"),
        )
        suspended = resp.dates[1].games[0]
        assert suspended.status.detailedState == "Suspended"
        assert suspended.isTie is True
        assert suspended.linescore is not None
        assert suspended.linescore.currentInning == 7

    def test_extra_fields_rejected(self):
        """Strict validation must reject unexpected fields (API drift)."""
        with pytest.raises(ValidationError, match="newUnexpectedField"):
            ScheduleResponse.model_validate_json(
                _read("schedule_extra_fields.json"),
            )


# ── Boxscore ─────────────────────────────────────────────────────────────


class TestBoxscoreResponse:
    """Validate BoxscoreResponse against frozen fixtures."""

    def test_typical(self):
        resp = BoxscoreResponse.model_validate_json(
            _read("boxscore_typical.json"),
        )
        assert resp.gamePk == 745678
        assert resp.gameData.status.detailedState == "Final"
        assert resp.liveData.linescore.currentInning == 9
        assert len(resp.liveData.linescore.innings) == 9
        # Decisions present
        assert resp.liveData.decisions is not None
        assert resp.liveData.decisions.winner is not None
        assert resp.liveData.decisions.winner.fullName == "Gerrit Cole"
        # Boxscore team data
        assert len(resp.liveData.boxscore.teams.away.batters) == 3
        assert len(resp.liveData.boxscore.officials) == 2

    def test_edge_case_postponed(self):
        resp = BoxscoreResponse.model_validate_json(
            _read("boxscore_edge_case.json"),
        )
        assert resp.gamePk == 746200
        assert resp.gameData.status.detailedState == "Postponed"
        assert resp.gameData.status.reason == "Rain"
        # No innings played
        assert len(resp.liveData.linescore.innings) == 0
        # No decisions
        assert resp.liveData.decisions is None
        # Empty boxscore
        assert resp.liveData.boxscore.teams.away.batters == []
        assert resp.metaData is None


# ── Content ──────────────────────────────────────────────────────────────


class TestContentResponse:
    """Validate ContentResponse against frozen fixtures."""

    def test_typical(self):
        resp = ContentResponse.model_validate_json(
            _read("content_typical.json"),
        )
        assert resp.link == "/api/v1/game/745678/content"
        # Editorial present
        assert resp.editorial is not None
        assert resp.editorial.recap is not None
        assert resp.editorial.recap.items is not None
        headline = resp.editorial.recap.items[0].headline
        assert headline == "Yankees power past Red Sox, 5-3"
        # Highlights with mp4 URLs
        assert resp.highlights is not None
        assert resp.highlights.highlights is not None
        items = resp.highlights.highlights.items
        assert items is not None
        assert len(items) == 2
        playback = items[0].playbacks[0]
        assert playback.name == "mp4Avc"
        assert playback.url.endswith(".mp4")
        # EPG extended highlights
        assert resp.media is not None
        assert resp.media.epg is not None
        epg_ext = [e for e in resp.media.epg if e.title == "Extended Highlights"]
        assert len(epg_ext) == 1
        assert epg_ext[0].items[0].playbacks is not None
        assert epg_ext[0].items[0].playbacks[0].url.endswith(".mp4")

    def test_edge_case_no_highlights(self):
        resp = ContentResponse.model_validate_json(
            _read("content_edge_case.json"),
        )
        # Editorial sections are null
        assert resp.editorial is not None
        assert resp.editorial.recap is None
        assert resp.editorial.articles is None
        # Media EPG is empty
        assert resp.media is not None
        assert resp.media.epg == []
        # Highlights container exists but items are empty
        assert resp.highlights is not None
        assert resp.highlights.highlights is not None
        assert resp.highlights.highlights.items == []
