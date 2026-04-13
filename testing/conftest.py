"""Shared pytest fixtures for frozen MLB API and S3 testing."""

from __future__ import annotations

import copy
import json
from functools import cache
from pathlib import Path

import pytest
import requests
from moto import mock_aws

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_BUCKET = "catch-data-test-bucket"
HTTP_REASONS = {
    404: "not found",
    500: "internal server error",
}


@cache
def load_fixture(name: str) -> dict:
    """Load a frozen JSON fixture once per Python process.

    Shared test fixtures are session-scoped, so caching keeps repeated file
    reads out of large test runs while still letting callers opt into their
    own defensive copies when they need to mutate fixture data.
    """
    with (FIXTURES_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def _http_error(status_code: int, url: str) -> requests.HTTPError:
    """Build an HTTPError with a populated response object."""
    response = requests.Response()
    response.status_code = status_code
    response.url = url
    response.reason = HTTP_REASONS.get(status_code, "error")
    return requests.HTTPError(response=response)


class FrozenMlbClient:
    """Mock MLB client backed by frozen fixture data."""

    def __init__(self) -> None:
        self._fixtures = {
            "schedule": "schedule_2025.json",
            "boxscore": "boxscore_normal.json",
            "content": "content_with_video.json",
        }
        self._behaviors = {
            "schedule": "success",
            "boxscore": "success",
            "content": "success",
        }

    def set_behavior(
        self,
        endpoint: str,
        behavior: str,
        fixture_name: str | None = None,
    ) -> None:
        """Configure response behavior for an endpoint."""
        if endpoint not in self._behaviors:
            raise ValueError(f"Unknown endpoint: {endpoint}")
        if behavior not in {"success", "404", "500", "timeout"}:
            raise ValueError(f"Unsupported behavior: {behavior}")
        self._behaviors[endpoint] = behavior
        if fixture_name is not None:
            self._fixtures[endpoint] = fixture_name

    def _dispatch(self, endpoint: str, url: str) -> dict:
        behavior = self._behaviors[endpoint]
        if behavior == "timeout":
            raise requests.Timeout(f"Timed out fetching {url}")
        if behavior == "404":
            raise _http_error(404, url)
        if behavior == "500":
            raise _http_error(500, url)
        return copy.deepcopy(load_fixture(self._fixtures[endpoint]))

    def get_schedule(self, year: int) -> dict:
        """Return a frozen schedule response."""
        return self._dispatch("schedule", f"/api/v1/schedule?season={year}")

    def get_boxscore(self, game_pk: int) -> dict:
        """Return a frozen boxscore response."""
        return self._dispatch("boxscore", f"/api/v1.1/game/{game_pk}/feed/live")

    def get_content(self, game_pk: int) -> dict:
        """Return a frozen content response."""
        return self._dispatch("content", f"/api/v1/game/{game_pk}/content")


@pytest.fixture(scope="session")
def sample_schedule() -> dict:
    """Load the default shared schedule fixture once per test session."""
    return load_fixture("schedule_2025.json")


@pytest.fixture(scope="session")
def sample_boxscore() -> dict:
    """Load the default shared boxscore fixture once per test session."""
    return load_fixture("boxscore_normal.json")


@pytest.fixture(scope="session")
def sample_content() -> dict:
    """Load the default shared content fixture once per test session."""
    return load_fixture("content_with_video.json")


@pytest.fixture
def mock_mlb_client() -> FrozenMlbClient:
    """Return a configurable frozen MLB client for offline testing."""
    return FrozenMlbClient()


@pytest.fixture
def mock_s3_client():
    """Return a moto-backed S3 client with a test bucket pre-created."""
    import boto3

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=TEST_BUCKET)
        yield client
