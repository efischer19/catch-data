# feat: Implement schedule ingestion to Bronze S3 layer

## What do you want to build?

Implement the Click CLI command in `apps/catch-ingestion` that fetches the
current season's full schedule from the MLB Stats API and uploads the raw JSON
response to the Bronze S3 bucket. This is the primary daily ingestion job that
keeps the schedule data current.

## Acceptance Criteria

- [ ] The `catch-ingestion ingest-schedule` CLI command fetches the full season schedule for a given year
- [ ] The raw JSON response is uploaded to S3 at the key returned by `CatchPaths.bronze_schedule_key(year)`
- [ ] The upload uses `boto3` S3 client with `ContentType: application/json`
- [ ] The command accepts `--year` as a CLI option (defaults to current year)
- [ ] The command logs the S3 key, file size, and number of games found at INFO level
- [ ] If the API returns an error, the command exits with a non-zero exit code and logs the failure
- [ ] Unit tests mock both the MLB API client and S3 upload, verifying the end-to-end flow
- [ ] Integration test (can be marked `@pytest.mark.integration`) verifies S3 upload with moto or localstack
- [ ] All tests pass via `poetry run pytest` in `apps/catch-ingestion`

## Implementation Notes

The schedule endpoint URL pattern is:
`https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={year}&hydrate=team,venue`

The `sportId=1` parameter filters to MLB (excludes minor leagues). The
`hydrate=team,venue` parameter inlines team and venue details, reducing the need
for follow-up API calls.

**😴 Lazy Maintainer notes:**

- The schedule is overwritten daily, not appended. The S3 key is
  `bronze/schedule_{year}.json` — same key every night. S3 versioning (enabled
  in Terraform) preserves historical versions automatically.
- Season rollover: when the year changes (January 1), the `--year` default
  naturally advances. No manual intervention needed. However, consider that
  in late October/November, postseason games may still be in progress from the
  previous year.

**⚾ Baseball Edge-Case Hunter notes:**

- Early in the season (March/April), the schedule includes Spring Training
  games if `gameType` is not filtered. Filter or tag them so downstream layers
  can exclude them.
- The schedule includes postponed games that may be rescheduled to a future
  date with a new `gamePk`. The raw response preserves both the original and
  rescheduled entries.

**🤑 FinOps Miser notes:**

- S3 PUT costs are $0.005 per 1,000 requests. One daily PUT is negligible.
- The raw schedule JSON for a full season is typically 2-5 MB. S3 storage
  cost is $0.023/GB/month — effectively free.

**🔧 Data Pipeline Janitor notes:**

- Upload is idempotent. Re-running the command for the same year simply
  overwrites the same S3 key with the latest data. No cleanup needed.

Use `click.option` for the `--year` parameter. Use `boto3` for S3 upload. Both
are expected dependencies per the ADR stack.
