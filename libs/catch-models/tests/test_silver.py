"""Tests for Silver-layer MLB game models."""

import json

import pytest

from catch_models import (
    DataCompleteness,
    SilverGame,
    SilverMasterSchedule,
    SilverProcessingErrors,
)


def test_silver_game_validates_realistic_final_game():
    """SilverGame should parse a realistic final game payload."""
    payload = {
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

    game = SilverGame.model_validate(payload)
    dumped = game.model_dump(mode="json")

    assert game.game_pk == 745678
    assert game.home_team_abbreviation == "NYY"
    assert game.data_completeness is DataCompleteness.FULL
    assert dumped["gamePk"] == 745678
    assert dumped["date"] == "2026-07-04T17:05:00Z"
    assert dumped["source_updated_at"] == "2026-07-05T01:17:00Z"
    assert dumped["condensed_game_url"].endswith("condensed-game.mp4")


def test_silver_game_accepts_postponed_doubleheader_without_boxscore():
    """Postponed or not-started games should allow null boxscore fields."""
    game = SilverGame.model_validate(
        {
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
        },
    )

    assert game.game_number == 2
    assert game.doubleheader_type == "S"
    assert game.status_detail == "Postponed"
    assert game.away_runs is None
    assert game.condensed_game_url is None
    assert game.data_completeness is DataCompleteness.NONE


def test_silver_master_schedule_serializes_utc_metadata_and_schema():
    """Master schedule JSON and schema should be clean and serializable."""
    schedule = SilverMasterSchedule.model_validate(
        {
            "year": 2026,
            "last_updated": "2026-09-01T02:30:00-04:00",
            "games": [
                {
                    "gamePk": 750001,
                    "date": "2026-09-01T23:10:00Z",
                    "game_type": "A",
                    "game_number": 1,
                    "doubleheader_type": "N",
                    "away_team_id": 198,
                    "away_team_name": "American League All-Stars",
                    "away_team_abbreviation": "AL",
                    "home_team_id": 199,
                    "home_team_name": "National League All-Stars",
                    "home_team_abbreviation": "NL",
                    "venue_id": 2394,
                    "venue_name": "Dodger Stadium",
                    "status": "In Progress",
                    "status_detail": "In Progress",
                    "current_inning": 10,
                    "inning_state": "Top",
                    "innings": 10,
                    "away_runs": 4,
                    "away_hits": 11,
                    "away_errors": 0,
                    "home_runs": 4,
                    "home_hits": 10,
                    "home_errors": 1,
                    "winning_pitcher_name": None,
                    "losing_pitcher_name": None,
                    "save_pitcher_name": None,
                    "condensed_game_url": None,
                    "source_updated_at": "2026-09-01T23:45:00Z",
                    "data_completeness": "partial",
                },
            ],
            "processing_errors": {
                "count": 1,
                "gamePks": [750002],
            },
        },
    )

    schema = SilverMasterSchedule.model_json_schema()
    dumped = schedule.model_dump(mode="json")

    assert dumped["last_updated"] == "2026-09-01T06:30:00Z"
    assert dumped["games"][0]["gamePk"] == 750001
    assert dumped["games"][0]["innings"] == 10
    assert dumped["games"][0]["data_completeness"] == "partial"
    assert dumped["processing_errors"] == {"count": 1, "gamePks": [750002]}
    assert schema["properties"]["last_updated"]["format"] == "date-time"
    assert schema["properties"]["games"]["items"]["$ref"] == "#/$defs/SilverGame"
    assert "gamePk" in schema["$defs"]["SilverGame"]["properties"]
    json.dumps(schema)


def test_silver_processing_errors_requires_matching_count():
    """Processing error summaries should be internally consistent."""
    summary = SilverProcessingErrors(count=2, gamePks=[745678, 745679])

    assert summary.count == 2
    assert summary.game_pks == [745678, 745679]

    with pytest.raises(ValueError, match="processing error count"):
        SilverProcessingErrors(count=1, gamePks=[745678, 745679])
