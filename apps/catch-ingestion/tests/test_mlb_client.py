"""Tests for the MLB Stats API client (ethical fetching)."""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from app.mlb_client import (
    MAX_RETRIES,
    USER_AGENT,
    MlbStatsClient,
    RetryableHTTPError,
    RobotsDenied,
    WaitRetryAfterOrExponential,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_robots_response(allowed: bool = True):
    """Return a mock RobotFileParser that allows/disallows all paths."""
    parser = MagicMock()
    parser.can_fetch.return_value = allowed
    return parser


def _ok_response(json_body: dict | None = None, status_code: int = 200):
    """Build a fake ``requests.Response`` with the given JSON body."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body or {"ok": True}
    resp.raise_for_status.return_value = None
    return resp


def _error_response(status_code: int):
    """Build a fake ``requests.Response`` that signals an error."""
    resp = MagicMock(spec=requests.Response)
    resp.headers = CaseInsensitiveDict()
    resp.status_code = status_code
    resp.json.return_value = {}
    resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    return resp


# ---------------------------------------------------------------------------
# User-Agent header
# ---------------------------------------------------------------------------


class TestUserAgent:
    def test_session_has_correct_user_agent(self):
        """The session must carry the honest User-Agent from ROBOT_ETHICS."""
        client = MlbStatsClient()
        assert client._session.headers["User-Agent"] == USER_AGENT

    def test_user_agent_value(self):
        """The User-Agent matches the ROBOT_ETHICS.md specification."""
        assert USER_AGENT == (
            "catch-data/0.1 (+https://github.com/efischer19/catch-data)"
        )


# ---------------------------------------------------------------------------
# Throttling delay
# ---------------------------------------------------------------------------


class TestThrottling:
    def test_throttle_enforces_delay(self):
        """Consecutive requests must be separated by at least *delay* seconds."""
        client = MlbStatsClient(delay=0.3)
        client._robots_parser = _mock_robots_response()

        with patch.object(client._session, "get", return_value=_ok_response()):
            client._get("/api/v1/test")
            start = time.monotonic()
            client._get("/api/v1/test")
            elapsed = time.monotonic() - start

        assert elapsed >= 0.3

    def test_default_delay_is_one_second(self):
        """The default delay must be 1 second."""
        client = MlbStatsClient()
        assert client._delay == 1.0

    def test_custom_delay(self):
        """The delay is configurable via the constructor."""
        client = MlbStatsClient(delay=2.5)
        assert client._delay == 2.5


# ---------------------------------------------------------------------------
# Retry behaviour (Tenacity — ADR-010)
# ---------------------------------------------------------------------------


class TestRetry:
    def test_retries_on_429(self):
        """HTTP 429 triggers a retry; eventual success is returned."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()

        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = _error_response(429)
                resp.headers.update({"Retry-After": "7"})
                return resp
            return _ok_response({"recovered": True})

        with (
            patch.object(client._session, "get", side_effect=_side_effect),
            patch("app.mlb_client.time.sleep") as mock_sleep,
        ):
            result = client._get("/api/v1/test")

        assert result == {"recovered": True}
        assert call_count == 3
        assert mock_sleep.call_args_list == [((7.0,),), ((7.0,),)]

    def test_retries_on_5xx(self):
        """HTTP 500 triggers a retry; eventual success is returned."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()

        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return _error_response(500)
            return _ok_response({"ok": True})

        with patch.object(client._session, "get", side_effect=_side_effect):
            result = client._get("/api/v1/test")

        assert result == {"ok": True}
        assert call_count == 2

    def test_raises_after_max_retries(self):
        """After 3 attempts the RetryableHTTPError is reraised."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()

        with (
            patch.object(
                client._session,
                "get",
                return_value=_error_response(503),
            ),
            patch("app.mlb_client.time.sleep"),
            pytest.raises(RetryableHTTPError) as exc_info,
        ):
            client._get("/api/v1/test")

        assert exc_info.value.retry_attempts == MAX_RETRIES + 1

    def test_non_retryable_error_raises_immediately(self):
        """HTTP 404 must *not* be retried — raise immediately."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()

        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = _error_response(404)
            return resp

        with (
            patch.object(client._session, "get", side_effect=_side_effect),
            pytest.raises(requests.HTTPError),
        ):
            client._get("/api/v1/test")

        assert call_count == 1

    def test_retries_on_connection_error(self):
        """Connection errors should be retried as transient failures."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()

        with (
            patch.object(
                client._session,
                "get",
                side_effect=[
                    requests.ConnectionError("boom"),
                    _ok_response({"ok": True}),
                ],
            ),
            patch("app.mlb_client.time.sleep"),
        ):
            assert client._get("/api/v1/test") == {"ok": True}

        assert client.api_call_count == 2

    def test_before_sleep_log_emits_retry_message(
        self,
        caplog: pytest.LogCaptureFixture,
    ):
        """Retry delays should be visible in logs via before_sleep_log."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()
        caplog.set_level(logging.WARNING, logger="app.mlb_client")

        with (
            patch.object(
                client._session,
                "get",
                side_effect=[requests.Timeout("boom"), _ok_response({"ok": True})],
            ),
            patch("app.mlb_client.time.sleep"),
        ):
            assert client._get("/api/v1/test") == {"ok": True}

        assert "Retrying app.mlb_client.MlbStatsClient._get_with_retry" in caplog.text


# ---------------------------------------------------------------------------
# robots.txt compliance
# ---------------------------------------------------------------------------


class TestRobotsTxt:
    def test_robots_txt_loaded_on_first_request(self):
        """robots.txt is fetched exactly once, on the first API call."""
        client = MlbStatsClient(delay=0)

        parser = _mock_robots_response(allowed=True)
        with (
            patch(
                "app.mlb_client.urllib.robotparser.RobotFileParser",
                return_value=parser,
            ),
            patch.object(client._session, "get", return_value=_ok_response()),
        ):
            client._get("/api/v1/test")
            client._get("/api/v1/test")

        # read() should only have been called once (first use)
        parser.read.assert_called_once()

    def test_disallowed_path_raises(self):
        """If robots.txt disallows a path, RobotsDenied is raised."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response(allowed=False)

        with pytest.raises(RobotsDenied, match="robots.txt disallows"):
            client._get("/api/v1/secret")

    def test_allowed_path_succeeds(self):
        """If robots.txt allows a path, the request proceeds normally."""
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response(allowed=True)

        with patch.object(
            client._session, "get", return_value=_ok_response({"data": 1})
        ):
            result = client._get("/api/v1/schedule")

        assert result == {"data": 1}


# ---------------------------------------------------------------------------
# Public API methods — return raw JSON dicts
# ---------------------------------------------------------------------------


class TestPublicMethods:
    def _make_client(self):
        client = MlbStatsClient(delay=0)
        client._robots_parser = _mock_robots_response()
        return client

    def test_get_schedule_returns_dict(self):
        """get_schedule returns the raw JSON dict for a season."""
        client = self._make_client()
        expected = {"dates": []}

        with patch.object(
            client._session, "get", return_value=_ok_response(expected)
        ) as mock_get:
            result = client.get_schedule(2024)

            assert result == expected
            call_url = mock_get.call_args[0][0]
            assert "/api/v1/schedule" in call_url
            assert "sportId=1" in call_url
            assert "season=2024" in call_url
            assert "hydrate=team,venue" in call_url

    def test_get_boxscore_returns_dict(self):
        """get_boxscore returns the raw JSON dict for a game."""
        client = self._make_client()
        expected = {"gamePk": 12345}

        with patch.object(
            client._session, "get", return_value=_ok_response(expected)
        ) as mock_get:
            result = client.get_boxscore(12345)

            assert result == expected
            call_url = mock_get.call_args[0][0]
            assert "/api/v1.1/game/12345/feed/live" in call_url

    def test_get_content_returns_dict(self):
        """get_content returns the raw JSON dict for game content."""
        client = self._make_client()
        expected = {"editorial": {}}

        with patch.object(
            client._session, "get", return_value=_ok_response(expected)
        ) as mock_get:
            result = client.get_content(99999)

            assert result == expected
            call_url = mock_get.call_args[0][0]
            assert "/api/v1/game/99999/content" in call_url


def test_retry_wait_uses_retry_after_header():
    """Retry-After should override exponential backoff when present."""
    response = _error_response(429)
    response.headers.update({"Retry-After": "11"})
    retry_state = MagicMock()
    retry_state.outcome.exception.return_value = RetryableHTTPError(response=response)

    wait_strategy = WaitRetryAfterOrExponential()

    assert wait_strategy(retry_state) == 11
