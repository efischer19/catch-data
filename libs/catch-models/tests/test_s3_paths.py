"""Tests for the catch-data S3 key utilities."""

from catch_models.s3_paths import CatchPaths


def test_bronze_schedule_key():
    """Verify the bronze schedule key follows the PRD convention."""
    assert CatchPaths.bronze_schedule_key(2025) == "bronze/schedule_2025.json"


def test_bronze_boxscore_key():
    """Verify the bronze boxscore key follows the PRD convention."""
    assert CatchPaths.bronze_boxscore_key(745678) == "bronze/boxscore_745678.json"


def test_bronze_content_key():
    """Verify the bronze content key follows the PRD convention."""
    assert CatchPaths.bronze_content_key(745678) == "bronze/content_745678.json"


def test_silver_master_schedule_key():
    """Verify the silver master schedule key follows the PRD convention."""
    assert (
        CatchPaths.silver_master_schedule_key(2025)
        == "silver/master_schedule_2025.json"
    )


def test_gold_team_key():
    """Verify the gold team key follows the PRD convention."""
    assert CatchPaths.gold_team_key(147) == "gold/team_147.json"


def test_gold_upcoming_games_key():
    """Verify the gold upcoming games key follows the PRD convention."""
    assert CatchPaths.gold_upcoming_games_key() == "gold/upcoming_games.json"


def test_generated_keys_do_not_start_with_or_contain_double_slashes():
    """Verify generated keys remain flat, deterministic object keys."""
    keys = [
        CatchPaths.bronze_schedule_key(2025),
        CatchPaths.bronze_boxscore_key(745678),
        CatchPaths.bronze_content_key(745678),
        CatchPaths.silver_master_schedule_key(2025),
        CatchPaths.gold_team_key(147),
        CatchPaths.gold_upcoming_games_key(),
    ]

    assert keys == [
        "bronze/schedule_2025.json",
        "bronze/boxscore_745678.json",
        "bronze/content_745678.json",
        "silver/master_schedule_2025.json",
        "gold/team_147.json",
        "gold/upcoming_games.json",
    ]
    assert all(not key.startswith("/") for key in keys)
    assert all("//" not in key for key in keys)
