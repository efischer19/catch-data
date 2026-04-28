"""MLB Stats API HTTP client with ethical fetching.

Implements the project's Robot Ethics policy (meta/ROBOT_ETHICS.md):
- Honest User-Agent identification
- Polite throttling between requests
- Exponential backoff retry on transient failures (ADR-010: Tenacity)
- robots.txt compliance

All methods return raw JSON as Python dicts — Bronze layer contract
(no transformation).
"""

import logging
import time
import urllib.robotparser
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import requests
from tenacity import (
    RetryCallState,
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.wait import wait_base

logger = logging.getLogger(__name__)

USER_AGENT = "catch-data/0.1 (+https://github.com/efischer19/catch-data)"
BASE_URL = "https://statsapi.mlb.com"
DEFAULT_DELAY = 1.0  # seconds between consecutive requests
RETRY_EXPONENTIAL_BASE_SECONDS = 2
RETRY_MAX_SECONDS = 60
MAX_RETRIES = 5


class RobotsDenied(Exception):
    """Raised when a URL is disallowed by robots.txt."""


class RetryableHTTPError(requests.HTTPError):
    """HTTP error eligible for automatic retry (429 or 5xx)."""


def retry_sleep(seconds: float) -> None:
    """Wrapper around ``time.sleep`` that provides a mockable test seam."""
    time.sleep(seconds)


def _retry_after_seconds(retry_after: str) -> float | None:
    """Parse a Retry-After header into seconds."""
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        try:
            retry_after_datetime = parsedate_to_datetime(retry_after)
        except (TypeError, ValueError):
            return None
        if retry_after_datetime.tzinfo is None:
            retry_after_datetime = retry_after_datetime.replace(tzinfo=UTC)
        return max(
            (retry_after_datetime - datetime.now(tz=UTC)).total_seconds(),
            0.0,
        )


def _get_retry_after_seconds(error: BaseException) -> float | None:
    """Return the retry delay requested by an HTTP 429 response, if any."""
    if (
        not isinstance(error, RetryableHTTPError)
        or error.response is None
        or error.response.status_code != 429
    ):
        return None

    retry_after = error.response.headers.get("Retry-After")
    if not retry_after:
        return None

    return _retry_after_seconds(retry_after)


class WaitRetryAfterOrExponential(wait_base):
    """Use Retry-After for HTTP 429 when present, else exponential backoff."""

    def __init__(self) -> None:
        self._fallback = wait_exponential(
            multiplier=RETRY_EXPONENTIAL_BASE_SECONDS,
            min=RETRY_EXPONENTIAL_BASE_SECONDS,
            max=RETRY_MAX_SECONDS,
        )

    def __call__(self, retry_state: RetryCallState) -> float:
        if retry_state.outcome is not None:
            error = retry_state.outcome.exception()
            parsed_retry_after = _get_retry_after_seconds(error)
            if parsed_retry_after is not None:
                return min(parsed_retry_after, RETRY_MAX_SECONDS)

        return self._fallback(retry_state)


def _is_retryable_request_error(error: BaseException) -> bool:
    """Return whether an exception represents a transient HTTP failure."""
    return isinstance(
        error,
        (
            RetryableHTTPError,
            requests.ConnectionError,
            requests.Timeout,
        ),
    )


class MlbStatsClient:
    """Ethical HTTP client for the MLB Stats API.

    Parameters
    ----------
    base_url : str
        Root URL of the API (default ``https://statsapi.mlb.com``).
    delay : float
        Minimum seconds between consecutive requests (default 1.0).
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = DEFAULT_DELAY,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._delay = delay
        self._last_request_time: float | None = None
        self._robots_parser: urllib.robotparser.RobotFileParser | None = None
        self._api_call_count = 0

        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT

    # ------------------------------------------------------------------
    # robots.txt compliance
    # ------------------------------------------------------------------
    def _ensure_robots_loaded(self) -> None:
        """Fetch and parse robots.txt on first use."""
        if self._robots_parser is not None:
            return
        robots_url = f"{self._base_url}/robots.txt"
        self._robots_parser = urllib.robotparser.RobotFileParser()
        self._robots_parser.set_url(robots_url)
        try:
            self._robots_parser.read()
            logger.info("Loaded robots.txt from %s", robots_url)
        except Exception:
            logger.warning(
                "Failed to fetch robots.txt from %s; allowing all paths",
                robots_url,
            )
            self._robots_parser.allow_all = True

    def _check_robots(self, path: str) -> None:
        """Raise ``RobotsDenied`` if *path* is disallowed by robots.txt."""
        self._ensure_robots_loaded()
        url = f"{self._base_url}{path}"
        assert self._robots_parser is not None
        if not self._robots_parser.can_fetch(USER_AGENT, url):
            raise RobotsDenied(f"robots.txt disallows: {url}")

    # ------------------------------------------------------------------
    # Throttling
    # ------------------------------------------------------------------
    def _throttle(self) -> None:
        """Enforce the minimum delay between consecutive requests."""
        if self._last_request_time is not None:
            elapsed = time.monotonic() - self._last_request_time
            remaining = self._delay - elapsed
            if remaining > 0:
                logger.debug("Throttling: sleeping %.2fs", remaining)
                time.sleep(remaining)

    # ------------------------------------------------------------------
    # Core request method with retry
    # ------------------------------------------------------------------
    @retry(
        retry=retry_if_exception(_is_retryable_request_error),
        wait=WaitRetryAfterOrExponential(),
        stop=stop_after_attempt(MAX_RETRIES + 1),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=False,
        sleep=retry_sleep,
    )
    def _get_with_retry(self, path: str) -> dict:
        """Perform a GET request with throttling and retry.

        Parameters
        ----------
        path : str
            API path (e.g. ``"/api/v1/schedule"``).

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        RobotsDenied
            If the path is disallowed by ``robots.txt``.
        RetryableHTTPError
            If the server returns 429 or 5xx after exhausting retries.
        requests.HTTPError
            For other non-success HTTP status codes.
        """
        self._check_robots(path)
        self._throttle()

        url = f"{self._base_url}{path}"
        logger.info("GET %s", url)
        self._api_call_count += 1
        response = self._session.get(url, timeout=30)
        self._last_request_time = time.monotonic()

        if response.status_code == 429 or response.status_code >= 500:
            error = RetryableHTTPError(response=response)
            logger.warning("Retryable HTTP %d for %s", response.status_code, url)
            raise error

        response.raise_for_status()
        return response.json()

    def _get(self, path: str) -> dict:
        """Perform a GET request with retry and attach final attempt metadata."""
        try:
            return self._get_with_retry(path)
        except RetryError as error:
            original_error = error.last_attempt.exception()
            if original_error is None:
                raise
            original_error.retry_attempts = error.last_attempt.attempt_number
            raise original_error from error

    @property
    def api_call_count(self) -> int:
        """Return the number of outbound API calls made by this client."""
        return self._api_call_count

    # ------------------------------------------------------------------
    # Public API methods — Bronze layer (raw JSON, no transformation)
    # ------------------------------------------------------------------
    def get_schedule(self, year: int) -> dict:
        """Fetch the full-season schedule for *year*.

        Parameters
        ----------
        year : int
            MLB season year (e.g. ``2024``).

        Returns
        -------
        dict
            Raw JSON response from the schedule endpoint.
        """
        path = f"/api/v1/schedule?sportId=1&season={year}&hydrate=team,venue"
        return self._get(path)

    def get_boxscore(self, game_pk: int) -> dict:
        """Fetch the boxscore for a specific game.

        Parameters
        ----------
        game_pk : int
            MLB game primary key.

        Returns
        -------
        dict
            Raw JSON response from the boxscore endpoint.
        """
        return self._get(f"/api/v1.1/game/{game_pk}/feed/live")

    def get_content(self, game_pk: int) -> dict:
        """Fetch editorial/media content for a specific game.

        Parameters
        ----------
        game_pk : int
            MLB game primary key.

        Returns
        -------
        dict
            Raw JSON response from the content endpoint.
        """
        return self._get(f"/api/v1/game/{game_pk}/content")
