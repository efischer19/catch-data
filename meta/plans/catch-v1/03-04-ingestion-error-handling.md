# feat: Add comprehensive error handling and resilience to ingestion

## What do you want to build?

Harden the ingestion pipeline with structured error handling, retry logic,
graceful degradation, and operational logging. The ingestion runs unattended on
a Mac Mini nightly — it must handle transient failures without human
intervention and clearly report persistent failures.

## Acceptance Criteria

- [ ] All API calls use Tenacity retry with exponential backoff (2s base, 60s max, 5 retries) per ADR-010
- [ ] Network errors (ConnectionError, Timeout) trigger retries; HTTP 4xx (except 429) do not
- [ ] HTTP 429 (rate limited) triggers retry with the `Retry-After` header value if present
- [ ] Each failed game is logged with structured JSON (gamePk, error type, attempt count) per ADR-008
- [ ] A summary report is logged at the end of each run: games processed, succeeded, failed, skipped
- [ ] The CLI exit code reflects overall status: 0 = all succeeded, 1 = partial failures, 2 = total failure
- [ ] A `--dry-run` flag logs what would be fetched/uploaded without making API calls or S3 writes
- [ ] Failed game PKs are written to a `failed_games.json` file locally for manual retry
- [ ] Unit tests verify retry behavior, error classification, and summary reporting
- [ ] All tests pass via `poetry run pytest` in `apps/catch-ingestion`

## Implementation Notes

**😴 Lazy Maintainer notes:**

- The partial failure exit code (1) allows the cron job to alert on failures
  while not blocking subsequent pipeline steps. A morning-after check of
  the ingestion log should be the only manual task.
- The `failed_games.json` output enables easy re-processing:
  `cat failed_games.json | xargs -I{} catch-ingestion ingest-games --game-pk {}`
- Consider sending a notification (email, webhook) on persistent failures.
  This can be a follow-up ticket if the team decides on a notification
  channel.

**🔧 Data Pipeline Janitor notes:**

- Retry logic must be idempotent. Re-uploading the same JSON to the same S3
  key is safe because S3 PUT is atomic and Bronze data is immutable.
- The `--dry-run` flag is critical for debugging. It should exercise the full
  code path up to (but not including) the actual HTTP request and S3 write.
- Structured logging must include a correlation ID (e.g., the run date) so
  all log entries from a single nightly run can be correlated.

**🤝 API Ethicist notes:**

- If the MLB API returns consistent 5xx errors (server down), the retry logic
  should not hammer the server. After max retries, back off entirely and log
  the failure. Do not implement infinite retry loops.
- Log a warning if the total number of API calls in a single run exceeds a
  configurable threshold (e.g., 100 calls). This protects against accidental
  over-fetching due to a bug.

**🧪 QA notes:**

- Use `tenacity.before_sleep_log` to make retry delays visible in test output
  without actually sleeping (mock `time.sleep` in tests).
- Test the exit code contract explicitly: a test that injects one failing game
  should verify exit code 1, not 0.

Reference ADR-010 (Tenacity) and ADR-008 (JSON structured logging).
