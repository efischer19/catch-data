Title: feat: Implement MLB Stats API HTTP client with ethical fetching

## What do you want to build?

Create a reusable HTTP client in `apps/catch-ingestion` for interacting with the
unofficial MLB Stats API (statsapi.mlb.com). The client must comply with the
project's Robot Ethics policy (ROBOT_ETHICS.md) by identifying itself honestly,
respecting rate limits, implementing polite throttling, and caching responses.

## Acceptance Criteria

- [ ] `app/mlb_client.py` (or similar) provides a `MlbStatsClient` class wrapping `requests.Session`
- [ ] The client sets a descriptive `User-Agent` header: `catch-data/0.1 (+https://github.com/efischer19/catch-data)`
- [ ] A configurable delay (default 1 second) is enforced between consecutive requests
- [ ] HTTP 429 and 5xx responses trigger exponential backoff retry (using Tenacity per ADR-010)
- [ ] The client exposes typed methods: `get_schedule(year)`, `get_boxscore(game_pk)`, `get_content(game_pk)`
- [ ] All methods return the raw JSON response as a Python dict (no transformation — Bronze layer contract)
- [ ] The client checks `robots.txt` for `statsapi.mlb.com` on first use and respects any `Disallow` directives
- [ ] Unit tests mock HTTP responses and verify: User-Agent header, retry behavior, throttling delay, robots.txt check
- [ ] All tests pass via `poetry run pytest` in `apps/catch-ingestion`

## Implementation Notes

**🤝 API Ethicist notes — IMPORTANT CONFLICT:**

The PRD says to "spoof a standard browser User-Agent to avoid CDN blocking."
The project's `meta/ROBOT_ETHICS.md` says to "use a descriptive User-Agent
string that clearly identifies the project." **These directly conflict.**

**Recommendation:** Follow ROBOT_ETHICS.md (honest User-Agent). If the honest
User-Agent is blocked by the MLB CDN, investigate alternatives (e.g., adding a
standard `Accept` header, using a different API endpoint) before resorting to
spoofing. Document the decision in an ADR.

**📝 ADR Consideration:**

- Propose an ADR documenting the User-Agent policy decision for MLB Stats API
  requests. This is a significant ethical and practical decision.

**🤝 API Ethicist notes (continued):**

- The MLB Stats API has no published rate limits. Default to 1 request/second
  as a conservative baseline, matching the "polite throttling" principle.
- Use Tenacity (ADR-010) with exponential backoff: start at 2 seconds, max
  60 seconds, max 5 retries.
- Log all HTTP requests at DEBUG level and all retries at WARNING level using
  JSON structured logging (ADR-008).

**⚾ Baseball Edge-Case Hunter notes:**

- The schedule endpoint returns the full 162-game season. For a team with
  doubleheaders, this may exceed 162 entries. The client should not paginate
  or truncate — return the complete response.
- Boxscore/content endpoints may return 404 for future games or games that
  have been postponed and rescheduled under a new `gamePk`. The client
  should return `None` (or raise a specific exception) for 404s, not retry.

Use `requests.Session` for connection pooling efficiency. Add `requests` and
`tenacity` as dependencies in `apps/catch-ingestion/pyproject.toml`.
