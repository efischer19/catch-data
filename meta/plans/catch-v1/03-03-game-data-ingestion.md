Title: feat: Implement boxscore and content ingestion to Bronze S3 layer

## What do you want to build?

Implement CLI commands in `apps/catch-ingestion` that fetch boxscore and
content/highlight data for recently completed games and upload the raw JSON
responses to the Bronze S3 bucket. This runs nightly after the schedule
ingestion and processes only games that reached "Final" status since the last
run.

## Acceptance Criteria

- [ ] `catch-ingestion ingest-games` CLI command identifies yesterday's completed games from the Bronze schedule file
- [ ] For each completed game, fetches the boxscore JSON and uploads to `bronze/boxscore_{gamePk}.json`
- [ ] For each completed game, fetches the content JSON and uploads to `bronze/content_{gamePk}.json`
- [ ] Already-ingested games (existing S3 keys) are skipped to avoid redundant API calls
- [ ] The command accepts `--date` to override the target date (defaults to yesterday)
- [ ] Progress is logged: total games found, games to process, games skipped, games uploaded
- [ ] HTTP 404 for a game's content (no highlights yet) is handled gracefully — logged as a warning, not an error
- [ ] Polite throttling (1 second between requests) is enforced across all API calls
- [ ] Unit tests mock the API client, S3 reads (for skip check), and S3 writes
- [ ] All tests pass via `poetry run pytest` in `apps/catch-ingestion`

## Implementation Notes

**API endpoints:**

- Boxscore: `https://statsapi.mlb.com/api/v1/game/{gamePk}/boxscore`
- Content: `https://statsapi.mlb.com/api/v1/game/{gamePk}/content`

The content response contains a deeply nested structure. The condensed game
video is typically at `highlights.highlights.items[].playbacks[]` where the
item's `type` is "condensed" and the playback's `name` is "mp4Avc". The Bronze
layer stores the full raw response — extraction happens in Silver.

**⚾ Baseball Edge-Case Hunter notes:**

- **Doubleheaders:** Two games on the same date means two boxscores and two
  content fetches. The command must iterate all completed games, not assume
  one-per-day.
- **Rainouts/Postponements:** Games with status "Postponed" have no boxscore.
  Skip these — only fetch for games with status "Final".
- **Late games:** West coast games ending after midnight ET may not have
  "Final" status at 3 AM ET. The `--date` parameter allows re-running for a
  previous date to catch these.
- **Suspended games:** A suspended game may show as "Final" only after its
  completion date. The skip check (S3 key exists) prevents duplicate processing.

**🤝 API Ethicist notes:**

- A typical day has 15 games, requiring 30 API calls (15 boxscore + 15
  content). With 1-second throttling, this takes ~30 seconds. Acceptable.
- On heavy days (doubleheaders across the league), this could reach 40+ calls.
  Still under 1 minute — well within polite limits.

**🔧 Data Pipeline Janitor notes:**

- The skip check (`s3.head_object` to see if key exists) prevents wasted API
  calls and is idempotent. If a boxscore needs refreshing (e.g., stat
  correction), add a `--force` flag to bypass the skip check.
- If a single game fails (API error), log the error and continue to the next
  game. Do not abort the entire batch for one failure.

**🤑 FinOps Miser notes:**

- S3 HEAD requests (for skip check) cost $0.0004 per 1,000. Negligible.
- S3 PUT for 30 files/day × 365 days = ~11,000 PUTs/year = $0.06/year.
