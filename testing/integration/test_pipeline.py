"""End-to-end pipeline integration tests: Bronze → Silver → Gold.

These tests validate the complete data flow using mocked S3 (via moto)
and frozen MLB API fixtures stored in ``testing/fixtures/``.  They are
the "acceptance tests" for the whole pipeline — if these pass we have
high confidence that nightly runs will produce correct output.

Run all integration tests with::

    poetry run pytest -m integration

from the ``testing/integration/`` directory.

Acceptance criteria verified
-----------------------------
* Bronze fixtures uploaded to in-memory S3.
* Silver Lambda logic writes ``silver/master_schedule_{year}.json``.
* Gold Lambda logic writes all 30 ``gold/team_{teamId}.json`` files and
  ``gold/upcoming_games.json``.
* Gold outputs validate against Pydantic models.
* Gold outputs validate against the generated JSON Schema.
* Doubleheader edge case: two games for the same team on the same date
  appear correctly with ``game_number`` 1 and 2.
* Missing-content edge case: a game without a condensed video has
  ``condensed_game_url: null`` in the Gold output.
* Negative test: a malformed Bronze boxscore is excluded gracefully;
  the Silver pipeline still produces output for the remaining games.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import jsonschema
import pytest
from catch_models import CatchPaths, GoldTeamSchedule, GoldUpcomingGames
from catch_models.schema import build_schema
from moto import mock_aws

# ---------------------------------------------------------------------------
# Load both app modules under unique names to avoid the shared ``app``
# package-name collision (both apps expose ``app.main``).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_app_main(app_path: Path, unique_name: str) -> Any:
    """Load ``app/main.py`` from *app_path* under *unique_name* in sys.modules."""
    main_path = app_path / "app" / "main.py"
    spec = importlib.util.spec_from_file_location(unique_name, main_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_processing_main = _load_app_main(
    _REPO_ROOT / "apps" / "catch-processing", "processing_main"
)
_analytics_main = _load_app_main(
    _REPO_ROOT / "apps" / "catch-analytics", "analytics_main"
)

# ---------------------------------------------------------------------------
# Fixture file → Bronze S3 key mapping
# ---------------------------------------------------------------------------

_SHARED_FIXTURES = _REPO_ROOT / "testing" / "fixtures"
_YEAR = 2025
_BUCKET = "catch-data-integration-test"

# Pin execution time inside the 2025 season so the rolling upcoming-games
# window is deterministic: 2025-07-19 through 2025-07-27.
_EXECUTION_TIME = datetime(2025, 7, 20, 12, 0, 0, tzinfo=UTC)

# (fixture filename, Bronze S3 key) pairs uploaded before every pipeline run.
_BRONZE_UPLOADS: list[tuple[str, str]] = [
    ("schedule_2025.json", CatchPaths.bronze_schedule_key(_YEAR)),
    # boxscores ---------------------------------------------------------------
    ("boxscore_spring_training.json", CatchPaths.bronze_boxscore_key(751001)),
    ("boxscore_normal.json", CatchPaths.bronze_boxscore_key(752400)),
    ("boxscore_doubleheader_g1.json", CatchPaths.bronze_boxscore_key(752100)),
    ("boxscore_doubleheader_g2.json", CatchPaths.bronze_boxscore_key(752101)),
    ("boxscore_postponed.json", CatchPaths.bronze_boxscore_key(752200)),
    ("boxscore_extra_innings.json", CatchPaths.bronze_boxscore_key(752300)),
    # content -----------------------------------------------------------------
    ("content_spring_training.json", CatchPaths.bronze_content_key(751001)),
    ("content_with_video.json", CatchPaths.bronze_content_key(752400)),
    # Re-use content_with_video for DH G1; the content link field is not
    # validated against the game_pk by the processing logic.
    ("content_with_video.json", CatchPaths.bronze_content_key(752100)),
    ("content_no_video.json", CatchPaths.bronze_content_key(752101)),
    ("content_postponed.json", CatchPaths.bronze_content_key(752200)),
    ("content_extra_innings.json", CatchPaths.bronze_content_key(752300)),
]

# All 30 current MLB team IDs (matches the Gold analytics layer's team map).
_MLB_TEAM_IDS: tuple[int, ...] = (
    108,
    109,
    110,
    111,
    112,
    113,
    114,
    115,
    116,
    117,
    118,
    119,
    120,
    121,
    133,
    134,
    135,
    136,
    137,
    138,
    139,
    140,
    141,
    142,
    143,
    144,
    145,
    146,
    147,
    158,
)

# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def _upload_bronze(s3_client: Any, bucket: str) -> None:
    """Upload all Bronze fixture files to the mocked S3 bucket."""
    for fixture_name, s3_key in _BRONZE_UPLOADS:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=(_SHARED_FIXTURES / fixture_name).read_bytes(),
            ContentType="application/json",
        )


def _run_silver(s3_client: Any, bucket: str) -> None:
    """Run Silver processing and persist the master schedule to S3."""
    master_schedule = _processing_main.build_master_schedule(
        s3_client, bucket, _YEAR, _EXECUTION_TIME
    )
    _processing_main.write_master_schedule_to_s3(s3_client, bucket, master_schedule)


def _run_gold(s3_client: Any, bucket: str) -> None:
    """Run Gold analytics and persist all Gold files to S3."""
    _analytics_main.generate_team_schedule_files(
        s3_client, bucket, _YEAR, _EXECUTION_TIME
    )


def _read_s3_json(s3_client: Any, bucket: str, key: str) -> dict:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return json.loads(response["Body"].read())


# ---------------------------------------------------------------------------
# Module-scoped pipeline fixture — runs the full Bronze → Silver → Gold
# pipeline once and shares the resulting S3 state across all tests that
# accept the ``pipeline_s3`` argument.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline_s3():
    """Moto-backed S3 client with a full Bronze → Silver → Gold run complete."""
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        _upload_bronze(client, _BUCKET)
        _run_silver(client, _BUCKET)
        _run_gold(client, _BUCKET)
        yield client


# ===========================================================================
# Silver layer
# ===========================================================================


@pytest.mark.integration
def test_silver_master_schedule_exists_in_s3(pipeline_s3):
    """Silver processing should write ``master_schedule_2025.json`` to S3."""
    key = CatchPaths.silver_master_schedule_key(_YEAR)
    data = _read_s3_json(pipeline_s3, _BUCKET, key)
    assert data["year"] == _YEAR
    assert isinstance(data["games"], list)
    assert len(data["games"]) > 0


@pytest.mark.integration
def test_silver_master_schedule_is_valid_pydantic_model(pipeline_s3):
    """Silver output should round-trip through the SilverMasterSchedule model."""
    from catch_models import SilverMasterSchedule

    key = CatchPaths.silver_master_schedule_key(_YEAR)
    body = pipeline_s3.get_object(Bucket=_BUCKET, Key=key)["Body"].read()
    schedule = SilverMasterSchedule.model_validate_json(body)
    assert schedule.year == _YEAR
    # The fixture schedule has exactly 6 games; all should process successfully.
    assert len(schedule.games) == 6
    assert schedule.processing_errors.count == 0


# ===========================================================================
# Gold layer — structural presence
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("team_id", _MLB_TEAM_IDS)
def test_gold_team_schedule_exists_for_all_teams(pipeline_s3, team_id):
    """Gold pipeline should produce ``team_{teamId}.json`` for all 30 MLB teams."""
    data = _read_s3_json(pipeline_s3, _BUCKET, CatchPaths.gold_team_key(team_id))
    assert data["team_id"] == team_id


@pytest.mark.integration
def test_gold_upcoming_games_exists_in_s3(pipeline_s3):
    """Gold pipeline should produce a valid ``upcoming_games.json``."""
    data = _read_s3_json(pipeline_s3, _BUCKET, CatchPaths.gold_upcoming_games_key())
    assert "games" in data
    assert "last_updated" in data


# ===========================================================================
# Gold layer — Pydantic model validation
# ===========================================================================


@pytest.mark.integration
def test_gold_team_schedules_valid_pydantic_models(pipeline_s3):
    """All 30 Gold team schedule files should be valid GoldTeamSchedule instances."""
    for team_id in _MLB_TEAM_IDS:
        body = pipeline_s3.get_object(
            Bucket=_BUCKET, Key=CatchPaths.gold_team_key(team_id)
        )["Body"].read()
        schedule = GoldTeamSchedule.model_validate_json(body)
        assert schedule.team_id == team_id


@pytest.mark.integration
def test_gold_upcoming_games_valid_pydantic_model(pipeline_s3):
    """Gold ``upcoming_games.json`` should deserialise as GoldUpcomingGames."""
    body = pipeline_s3.get_object(
        Bucket=_BUCKET, Key=CatchPaths.gold_upcoming_games_key()
    )["Body"].read()
    upcoming = GoldUpcomingGames.model_validate_json(body)
    assert isinstance(upcoming.games, list)
    # With _EXECUTION_TIME = 2025-07-20T12Z the rolling window covers
    # 2025-07-19 through 2025-07-27 — exactly the three games on 2025-07-20
    # (DH G1, DH G2, and the postponed game).
    assert len(upcoming.games) == 3


# ===========================================================================
# Gold layer — JSON Schema cross-validation
# ===========================================================================


@pytest.mark.integration
def test_gold_team_schedule_validates_against_json_schema(pipeline_s3):
    """Gold ``team_111.json`` (BOS) should conform to the generated JSON Schema."""
    schema = build_schema()
    data = _read_s3_json(pipeline_s3, _BUCKET, CatchPaths.gold_team_key(111))
    jsonschema.validate(instance=data, schema=schema)


@pytest.mark.integration
def test_gold_upcoming_games_validates_against_json_schema(pipeline_s3):
    """Gold ``upcoming_games.json`` should conform to the generated JSON Schema."""
    schema = build_schema()
    data = _read_s3_json(pipeline_s3, _BUCKET, CatchPaths.gold_upcoming_games_key())
    jsonschema.validate(instance=data, schema=schema)


# ===========================================================================
# Edge case: doubleheader
# ===========================================================================


@pytest.mark.integration
@pytest.mark.parametrize("team_id", [111, 147])  # BOS (home) and NYY (away)
def test_doubleheader_both_games_appear_in_gold_team_schedule(pipeline_s3, team_id):
    """Two doubleheader games on 2025-07-20 should appear with game_number 1 and 2."""
    body = pipeline_s3.get_object(
        Bucket=_BUCKET, Key=CatchPaths.gold_team_key(team_id)
    )["Body"].read()
    schedule = GoldTeamSchedule.model_validate_json(body)

    dh_games = [
        game
        for game in schedule.games
        if game.date.date().isoformat() == "2025-07-20" and game.game_number in {1, 2}
    ]
    assert len(dh_games) == 2, (
        f"Team {team_id}: expected 2 doubleheader games on 2025-07-20, "
        f"found {len(dh_games)}"
    )
    assert {g.game_number for g in dh_games} == {1, 2}


# ===========================================================================
# Edge case: missing condensed video
# ===========================================================================


@pytest.mark.integration
def test_game_without_condensed_video_has_null_url_in_gold(pipeline_s3):
    """Game 752101 (DH G2) uses ``content_no_video.json`` → condensed URL is null."""
    # NYY (147) appears as the away team in game 752101.
    body = pipeline_s3.get_object(Bucket=_BUCKET, Key=CatchPaths.gold_team_key(147))[
        "Body"
    ].read()
    schedule = GoldTeamSchedule.model_validate_json(body)

    dh_g2 = next((g for g in schedule.games if g.game_pk == 752101), None)
    assert dh_g2 is not None, "Game 752101 (DH G2) should appear in the NYY schedule"
    assert dh_g2.condensed_game_url is None, (
        f"DH G2 expected null condensed_game_url, got {dh_g2.condensed_game_url!r}"
    )


# ===========================================================================
# Edge case: postponed game
# ===========================================================================


@pytest.mark.integration
def test_postponed_game_has_correct_status_and_no_score(pipeline_s3):
    """Game 752200 (Postponed) should appear with status 'Postponed' and no score."""
    # NYM (121) was the home team for the postponed game.
    body = pipeline_s3.get_object(Bucket=_BUCKET, Key=CatchPaths.gold_team_key(121))[
        "Body"
    ].read()
    schedule = GoldTeamSchedule.model_validate_json(body)

    postponed = next((g for g in schedule.games if g.game_pk == 752200), None)
    assert postponed is not None, "Game 752200 should appear in the NYM Gold schedule"
    assert "Postponed" in postponed.status
    assert postponed.score is None


# ===========================================================================
# Negative test: malformed Bronze file
# ===========================================================================


@pytest.mark.integration
def test_malformed_bronze_boxscore_excluded_gracefully():
    """Silver should exclude a game with a malformed boxscore without crashing.

    The pipeline must still produce output for the remaining games, and the
    failed game_pk must appear in ``processing_errors.gamePks``.
    """
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=_BUCKET)
        _upload_bronze(client, _BUCKET)

        # Overwrite game 752400's boxscore with data that fails Pydantic validation.
        client.put_object(
            Bucket=_BUCKET,
            Key=CatchPaths.bronze_boxscore_key(752400),
            Body=b'{"this_is": "not a valid BoxscoreResponse"}',
            ContentType="application/json",
        )

        master_schedule = _processing_main.build_master_schedule(
            client, _BUCKET, _YEAR, _EXECUTION_TIME
        )

    # Pipeline should succeed and contain the remaining valid games.
    assert len(master_schedule.games) > 0
    # The malformed game should be recorded in processing_errors.
    assert 752400 in master_schedule.processing_errors.game_pks
