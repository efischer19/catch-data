"""MLB Stats API HTTP client with ethical fetching.

Implements the project's Robot Ethics policy (meta/ROBOT_ETHICS.md):
- Honest User-Agent identification
- Polite throttling between requests
- Exponential backoff retry on 429/5xx errors (ADR-010: Tenacity)
- robots.txt compliance

All methods return raw JSON as Python dicts — Bronze layer contract
(no transformation).
"""

import logging
import time
import urllib.robotparser

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

USER_AGENT = "catch-data/0.1 (+https://github.com/efischer19/catch-data)"
BASE_URL = "https://statsapi.mlb.com"
DEFAULT_DELAY = 1.0  # seconds between consecutive requests


class RobotsDenied(Exception):
    """Raised when a URL is disallowed by robots.txt."""


class RetryableHTTPError(requests.HTTPError):
    """HTTP error eligible for automatic retry (429 or 5xx)."""


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
        retry=retry_if_exception_type(RetryableHTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _get(self, path: str) -> dict:
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
        response = self._session.get(url, timeout=30)
        self._last_request_time = time.monotonic()

        if response.status_code == 429 or response.status_code >= 500:
            error = RetryableHTTPError(response=response)
            logger.warning("Retryable HTTP %d for %s", response.status_code, url)
            raise error

        response.raise_for_status()
        return response.json()

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
