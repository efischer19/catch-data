"""Tests for Gold-layer Pydantic models.

Validates:
- Model construction from raw keyword arguments
- Transformation contract: building Gold models from Silver model data
- JSON serialisation via ``model_dump(mode="json")``
- Edge cases: doubleheader, postponed game, missing video URL
- ``model_json_schema()`` produces clean, serialisable output
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from catch_models import (
    DataCompleteness,
    GoldBoxscoreSummary,
    GoldGameDateGroup,
    GoldGameSummary,
    GoldScore,
    GoldTeamInfo,
    GoldTeamSchedule,
    GoldUpcomingGames,
    SilverGame,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_AWAY_TEAM = GoldTeamInfo(
    id=111,
    name="Boston Red Sox",
    abbreviation="BOS",
    league="American League",
    division="AL East",
)
_HOME_TEAM = GoldTeamInfo(
    id=147,
    name="New York Yankees",
    abbreviation="NYY",
    league="American League",
    division="AL East",
)

_FINAL_GAME_PAYLOAD: dict = {
    "gamePk": 745678,
    "date": "2026-07-04T13:05:00-04:00",
    "game_type": "R",
    "game_number": 1,
    "doubleheader_type": "N",
    "away_team_id": 111,
    "away_team_name": "Boston Red Sox",
    "away_team_abbreviation": "BOS",
    "home_team_id": 147,
    "home_team_name": "New York Yankees",
    "home_team_abbreviation": "NYY",
    "venue_id": 3313,
    "venue_name": "Yankee Stadium",
    "status": "Final",
    "status_detail": "Final",
    "current_inning": 9,
    "inning_state": "End",
    "innings": 9,
    "away_runs": 3,
    "away_hits": 7,
    "away_errors": 1,
    "home_runs": 5,
    "home_hits": 9,
    "home_errors": 0,
    "winning_pitcher_name": "Gerrit Cole",
    "losing_pitcher_name": "Chris Sale",
    "save_pitcher_name": "Clay Holmes",
    "condensed_game_url": "https://mlb-cuts-diamond.mlb.com/FORGE/2026/2026-07/04/abcd/condensed-game.mp4",
    "source_updated_at": "2026-07-04T21:17:00-04:00",
    "data_completeness": "full",
}

_POSTPONED_GAME_PAYLOAD: dict = {
    "gamePk": 746200,
    "date": "2026-08-12T16:10:00Z",
    "game_type": "R",
    "game_number": 2,
    "doubleheader_type": "S",
    "away_team_id": 121,
    "away_team_name": "New York Mets",
    "away_team_abbreviation": "NYM",
    "home_team_id": 120,
    "home_team_name": "Washington Nationals",
    "home_team_abbreviation": "WSH",
    "venue_id": 3309,
    "venue_name": "Nationals Park",
    "status": "Postponed",
    "status_detail": "Postponed",
    "current_inning": None,
    "inning_state": None,
    "innings": None,
    "away_runs": None,
    "away_hits": None,
    "away_errors": None,
    "home_runs": None,
    "home_hits": None,
    "home_errors": None,
    "winning_pitcher_name": None,
    "losing_pitcher_name": None,
    "save_pitcher_name": None,
    "condensed_game_url": None,
    "source_updated_at": "2026-08-12T17:00:00Z",
    "data_completeness": "none",
}


def _silver_to_gold_game(silver: SilverGame, team_info: dict) -> GoldGameSummary:
    """Helper: transform a SilverGame into a GoldGameSummary.

    ``team_info`` is a dict mapping team_id → GoldTeamInfo (supplies
    league / division that are not present in the Silver layer).
    """
    has_score = silver.away_runs is not None and silver.home_runs is not None
    score = (
        GoldScore(away=silver.away_runs, home=silver.home_runs) if has_score else None
    )
    score_display = f"{silver.away_runs}-{silver.home_runs}" if has_score else None

    has_full_boxscore = silver.data_completeness is DataCompleteness.FULL and has_score
    boxscore = (
        GoldBoxscoreSummary(
            away_r=silver.away_runs,  # type: ignore[arg-type]
            away_h=silver.away_hits,  # type: ignore[arg-type]
            away_e=silver.away_errors,  # type: ignore[arg-type]
            home_r=silver.home_runs,  # type: ignore[arg-type]
            home_h=silver.home_hits,  # type: ignore[arg-type]
            home_e=silver.home_errors,  # type: ignore[arg-type]
            winning_pitcher=silver.winning_pitcher_name,
            losing_pitcher=silver.losing_pitcher_name,
            save_pitcher=silver.save_pitcher_name,
        )
        if has_full_boxscore
        else None
    )

    return GoldGameSummary(
        game_pk=silver.game_pk,
        date=silver.date,
        status=silver.status_detail,
        game_number=silver.game_number,
        venue_name=silver.venue_name,
        home_team=team_info[silver.home_team_id],
        away_team=team_info[silver.away_team_id],
        score=score,
        score_display=score_display,
        condensed_game_url=(
            str(silver.condensed_game_url) if silver.condensed_game_url else None
        ),
        boxscore_summary=boxscore,
    )


# ---------------------------------------------------------------------------
# GoldTeamInfo
# ---------------------------------------------------------------------------


class TestGoldTeamInfo:
    def test_round_trips_json(self):
        info = GoldTeamInfo(
            id=147,
            name="New York Yankees",
            abbreviation="NYY",
            league="American League",
            division="AL East",
        )
        dumped = info.model_dump(mode="json")
        assert dumped == {
            "id": 147,
            "name": "New York Yankees",
            "abbreviation": "NYY",
            "league": "American League",
            "division": "AL East",
        }

    def test_extra_fields_rejected(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GoldTeamInfo(
                id=1,
                name="X",
                abbreviation="X",
                league="X",
                division="X",
                unexpected_field="oops",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# GoldScore
# ---------------------------------------------------------------------------


class TestGoldScore:
    def test_basic_score(self):
        score = GoldScore(away=3, home=5)
        dumped = score.model_dump(mode="json")
        assert dumped == {"away": 3, "home": 5}


# ---------------------------------------------------------------------------
# GoldBoxscoreSummary
# ---------------------------------------------------------------------------


class TestGoldBoxscoreSummary:
    def test_full_boxscore_with_save(self):
        box = GoldBoxscoreSummary(
            away_r=3,
            away_h=7,
            away_e=1,
            home_r=5,
            home_h=9,
            home_e=0,
            winning_pitcher="Gerrit Cole",
            losing_pitcher="Chris Sale",
            save_pitcher="Clay Holmes",
        )
        dumped = box.model_dump(mode="json")
        assert dumped["away_r"] == 3
        assert dumped["home_r"] == 5
        assert dumped["winning_pitcher"] == "Gerrit Cole"
        assert dumped["save_pitcher"] == "Clay Holmes"

    def test_no_save_pitcher(self):
        box = GoldBoxscoreSummary(
            away_r=2,
            away_h=5,
            away_e=0,
            home_r=1,
            home_h=4,
            home_e=1,
            winning_pitcher="Shane McClanahan",
            losing_pitcher="Framber Valdez",
        )
        assert box.save_pitcher is None
        assert box.model_dump(mode="json")["save_pitcher"] is None


# ---------------------------------------------------------------------------
# GoldGameSummary
# ---------------------------------------------------------------------------


class TestGoldGameSummary:
    def test_final_game_all_fields(self):
        game = GoldGameSummary(
            game_pk=745678,
            date=datetime(2026, 7, 4, 17, 5, tzinfo=UTC),
            status="Final",
            game_number=1,
            venue_name="Yankee Stadium",
            home_team=_HOME_TEAM,
            away_team=_AWAY_TEAM,
            score=GoldScore(away=3, home=5),
            score_display="3-5",
            condensed_game_url="https://mlb-cuts-diamond.mlb.com/condensed-game.mp4",
            boxscore_summary=GoldBoxscoreSummary(
                away_r=3,
                away_h=7,
                away_e=1,
                home_r=5,
                home_h=9,
                home_e=0,
                winning_pitcher="Gerrit Cole",
                losing_pitcher="Chris Sale",
                save_pitcher="Clay Holmes",
            ),
        )
        dumped = game.model_dump(mode="json")

        assert dumped["game_pk"] == 745678
        assert dumped["date"] == "2026-07-04T17:05:00Z"
        assert dumped["status"] == "Final"
        assert dumped["game_number"] == 1
        assert dumped["venue_name"] == "Yankee Stadium"
        assert dumped["score"] == {"away": 3, "home": 5}
        assert dumped["score_display"] == "3-5"
        assert "condensed-game.mp4" in dumped["condensed_game_url"]
        assert dumped["boxscore_summary"]["away_r"] == 3
        assert dumped["boxscore_summary"]["winning_pitcher"] == "Gerrit Cole"
        assert dumped["home_team"]["abbreviation"] == "NYY"
        assert dumped["away_team"]["abbreviation"] == "BOS"

    def test_scheduled_game_nulls(self):
        """Pre-game summaries have null score, score_display, and boxscore."""
        game = GoldGameSummary(
            game_pk=799000,
            date=datetime(2026, 9, 15, 18, 10, tzinfo=UTC),
            status="Scheduled",
            game_number=1,
            venue_name="Yankee Stadium",
            home_team=_HOME_TEAM,
            away_team=_AWAY_TEAM,
        )
        dumped = game.model_dump(mode="json")
        assert dumped["score"] is None
        assert dumped["score_display"] is None
        assert dumped["condensed_game_url"] is None
        assert dumped["boxscore_summary"] is None

    def test_postponed_game(self):
        game = GoldGameSummary(
            game_pk=746200,
            date=datetime(2026, 8, 12, 16, 10, tzinfo=UTC),
            status="Postponed",
            game_number=2,
            venue_name="Nationals Park",
            home_team=_HOME_TEAM,
            away_team=_AWAY_TEAM,
        )
        assert game.status == "Postponed"
        assert game.game_number == 2
        assert game.score is None
        assert game.condensed_game_url is None

    def test_date_serialized_as_utc_iso(self):
        """Dates must be stored and serialised in UTC regardless of input offset."""
        game = GoldGameSummary(
            game_pk=1,
            date=datetime(2026, 7, 4, 13, 5, tzinfo=UTC),
            status="Final",
            game_number=1,
            venue_name="Yankee Stadium",
            home_team=_HOME_TEAM,
            away_team=_AWAY_TEAM,
        )
        dumped = game.model_dump(mode="json")
        assert dumped["date"].endswith("Z")


# ---------------------------------------------------------------------------
# GoldTeamSchedule
# ---------------------------------------------------------------------------


class TestGoldTeamSchedule:
    def test_empty_schedule(self):
        schedule = GoldTeamSchedule(
            team_id=147,
            team_name="New York Yankees",
            team_abbreviation="NYY",
            season_year=2026,
            last_updated=datetime(2026, 4, 1, 0, 0, tzinfo=UTC),
        )
        dumped = schedule.model_dump(mode="json")
        assert dumped["team_id"] == 147
        assert dumped["season_year"] == 2026
        assert dumped["games"] == []
        assert dumped["last_updated"].endswith("Z")

    def test_schedule_with_games(self):
        games = [
            GoldGameSummary(
                game_pk=745678,
                date=datetime(2026, 7, 4, 17, 5, tzinfo=UTC),
                status="Final",
                game_number=1,
                venue_name="Yankee Stadium",
                home_team=_HOME_TEAM,
                away_team=_AWAY_TEAM,
                score=GoldScore(away=3, home=5),
                score_display="3-5",
            ),
            GoldGameSummary(
                game_pk=745999,
                date=datetime(2026, 7, 5, 18, 5, tzinfo=UTC),
                status="Scheduled",
                game_number=1,
                venue_name="Yankee Stadium",
                home_team=_HOME_TEAM,
                away_team=_AWAY_TEAM,
            ),
        ]
        schedule = GoldTeamSchedule(
            team_id=147,
            team_name="New York Yankees",
            team_abbreviation="NYY",
            season_year=2026,
            last_updated=datetime(2026, 7, 5, 6, 0, tzinfo=UTC),
            games=games,
        )
        dumped = schedule.model_dump(mode="json")
        assert len(dumped["games"]) == 2
        assert dumped["games"][0]["game_pk"] == 745678
        assert dumped["games"][0]["score_display"] == "3-5"
        assert dumped["games"][1]["score"] is None

    def test_json_schema_is_serialisable(self):
        schema = GoldTeamSchedule.model_json_schema()
        json.dumps(schema)  # must not raise
        assert "properties" in schema
        assert "games" in schema["properties"]


# ---------------------------------------------------------------------------
# GoldUpcomingGames
# ---------------------------------------------------------------------------


class TestGoldUpcomingGames:
    def test_upcoming_games_round_trip(self):
        upcoming = GoldUpcomingGames(
            last_updated=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
            games=[
                GoldGameSummary(
                    game_pk=745678,
                    date=datetime(2026, 7, 4, 17, 5, tzinfo=UTC),
                    status="Final",
                    game_number=1,
                    venue_name="Yankee Stadium",
                    home_team=_HOME_TEAM,
                    away_team=_AWAY_TEAM,
                    score=GoldScore(away=3, home=5),
                    score_display="3-5",
                ),
            ],
        )
        dumped = upcoming.model_dump(mode="json")
        assert dumped["last_updated"] == "2026-07-05T12:00:00Z"
        assert len(dumped["games"]) == 1
        assert dumped["games"][0]["status"] == "Final"
        assert dumped["dates"] == [
            {
                "date": "2026-07-04",
                "games": [dumped["games"][0]],
            }
        ]

    def test_explicit_date_groups_are_preserved(self):
        game = GoldGameSummary(
            game_pk=745678,
            date=datetime(2026, 7, 4, 17, 5, tzinfo=UTC),
            status="Final",
            game_number=1,
            venue_name="Yankee Stadium",
            home_team=_HOME_TEAM,
            away_team=_AWAY_TEAM,
            score=GoldScore(away=3, home=5),
            score_display="3-5",
        )
        upcoming = GoldUpcomingGames(
            last_updated=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
            games=[game],
            dates=[
                GoldGameDateGroup(
                    date=datetime(2026, 7, 4, tzinfo=UTC).date(),
                    games=[game],
                )
            ],
        )

        dumped = upcoming.model_dump(mode="json")
        assert dumped["dates"][0]["date"] == "2026-07-04"
        assert dumped["dates"][0]["games"][0]["game_pk"] == 745678

    def test_explicit_date_groups_must_match_games(self):
        from pydantic import ValidationError

        game = GoldGameSummary(
            game_pk=745678,
            date=datetime(2026, 7, 4, 17, 5, tzinfo=UTC),
            status="Final",
            game_number=1,
            venue_name="Yankee Stadium",
            home_team=_HOME_TEAM,
            away_team=_AWAY_TEAM,
            score=GoldScore(away=3, home=5),
            score_display="3-5",
        )

        with pytest.raises(
            ValidationError,
            match="dates must match the grouped games list",
        ):
            GoldUpcomingGames(
                last_updated=datetime(2026, 7, 5, 12, 0, tzinfo=UTC),
                games=[game],
                dates=[GoldGameDateGroup(date=datetime(2026, 7, 5, tzinfo=UTC).date())],
            )

    def test_json_schema_is_serialisable(self):
        schema = GoldUpcomingGames.model_json_schema()
        json.dumps(schema)  # must not raise


# ---------------------------------------------------------------------------
# Transformation contract tests: Silver → Gold
# ---------------------------------------------------------------------------


class TestSilverToGoldTransformation:
    """Validate that Gold models can be constructed from Silver model data."""

    def _team_info(self) -> dict[int, GoldTeamInfo]:
        return {
            111: GoldTeamInfo(
                id=111,
                name="Boston Red Sox",
                abbreviation="BOS",
                league="American League",
                division="AL East",
            ),
            120: GoldTeamInfo(
                id=120,
                name="Washington Nationals",
                abbreviation="WSH",
                league="National League",
                division="NL East",
            ),
            121: GoldTeamInfo(
                id=121,
                name="New York Mets",
                abbreviation="NYM",
                league="National League",
                division="NL East",
            ),
            147: GoldTeamInfo(
                id=147,
                name="New York Yankees",
                abbreviation="NYY",
                league="American League",
                division="AL East",
            ),
        }

    def test_final_game_transformation(self):
        """Full Silver game record → GoldGameSummary with all fields populated."""
        silver = SilverGame.model_validate(_FINAL_GAME_PAYLOAD)
        gold = _silver_to_gold_game(silver, self._team_info())

        assert gold.game_pk == 745678
        assert gold.status == "Final"
        assert gold.game_number == 1
        assert gold.score is not None
        assert gold.score.away == 3
        assert gold.score.home == 5
        assert gold.score_display == "3-5"
        assert gold.condensed_game_url is not None
        assert "condensed-game.mp4" in gold.condensed_game_url
        assert gold.boxscore_summary is not None
        assert gold.boxscore_summary.away_r == 3
        assert gold.boxscore_summary.home_h == 9
        assert gold.boxscore_summary.winning_pitcher == "Gerrit Cole"
        assert gold.boxscore_summary.save_pitcher == "Clay Holmes"
        assert gold.home_team.abbreviation == "NYY"
        assert gold.away_team.abbreviation == "BOS"

        # Must serialise cleanly
        dumped = gold.model_dump(mode="json")
        assert dumped["date"] == "2026-07-04T17:05:00Z"
        json.dumps(dumped)

    def test_postponed_doubleheader_game_2_transformation(self):
        """Postponed Silver game → GoldGameSummary with null score fields."""
        silver = SilverGame.model_validate(_POSTPONED_GAME_PAYLOAD)
        gold = _silver_to_gold_game(silver, self._team_info())

        assert gold.game_pk == 746200
        assert gold.status == "Postponed"
        assert gold.game_number == 2
        assert gold.score is None
        assert gold.score_display is None
        assert gold.condensed_game_url is None
        assert gold.boxscore_summary is None

        dumped = gold.model_dump(mode="json")
        assert dumped["game_number"] == 2
        assert dumped["score"] is None
        json.dumps(dumped)

    def test_team_schedule_built_from_silver_games(self):
        """GoldTeamSchedule wraps multiple Silver-derived GoldGameSummary objects."""
        team_map = self._team_info()
        silver_games = [
            SilverGame.model_validate(_FINAL_GAME_PAYLOAD),
            SilverGame.model_validate(_POSTPONED_GAME_PAYLOAD),
        ]
        gold_games = [_silver_to_gold_game(g, team_map) for g in silver_games]

        schedule = GoldTeamSchedule(
            team_id=147,
            team_name="New York Yankees",
            team_abbreviation="NYY",
            season_year=2026,
            last_updated=datetime(2026, 8, 12, 18, 0, tzinfo=UTC),
            games=[
                g for g in gold_games if g.home_team.id == 147 or g.away_team.id == 147
            ],
        )
        dumped = schedule.model_dump(mode="json")
        assert dumped["team_id"] == 147
        assert dumped["season_year"] == 2026
        assert len(dumped["games"]) >= 1
        json.dumps(dumped)

    def test_upcoming_games_built_from_silver_games(self):
        """GoldUpcomingGames wraps a filtered list of Silver-derived summaries."""
        team_map = self._team_info()
        silver_games = [
            SilverGame.model_validate(_FINAL_GAME_PAYLOAD),
            SilverGame.model_validate(_POSTPONED_GAME_PAYLOAD),
        ]
        gold_games = [_silver_to_gold_game(g, team_map) for g in silver_games]

        upcoming = GoldUpcomingGames(
            last_updated=datetime(2026, 8, 12, 18, 0, tzinfo=UTC),
            games=gold_games,
        )
        dumped = upcoming.model_dump(mode="json")
        assert len(dumped["games"]) == 2
        assert [group["date"] for group in dumped["dates"]] == [
            "2026-07-04",
            "2026-08-12",
        ]
        statuses = {g["status"] for g in dumped["games"]}
        assert "Final" in statuses
        assert "Postponed" in statuses
        json.dumps(dumped)
