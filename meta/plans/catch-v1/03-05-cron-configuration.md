Title: feat: Configure Mac Mini cron job for nightly ingestion

## What do you want to build?

Create the cron job configuration and supporting scripts that run the ingestion
pipeline nightly on the local Mac Mini. The cron job should execute the schedule
ingestion followed by the game data ingestion, with proper environment setup,
logging, and error reporting.

## Acceptance Criteria

- [ ] A `scripts/nightly-ingest.sh` script orchestrates the full ingestion sequence: schedule first, then game data
- [ ] The script activates the correct Python/Poetry environment before running CLI commands
- [ ] AWS credentials are sourced from a secure location (e.g., `~/.aws/credentials` or environment variables) — never hardcoded
- [ ] The script writes timestamped logs to a configurable log directory (e.g., `~/catch-data-logs/`)
- [ ] A sample crontab entry is documented: `0 3 * * * /path/to/nightly-ingest.sh` (3:00 AM local time)
- [ ] The script handles the case where the Mac Mini was off (missed a night) by accepting a `--backfill-date` argument
- [ ] The script exits with a non-zero code if any ingestion step fails, suitable for cron error reporting
- [ ] A `README` or doc section in the repo documents the Mac Mini setup procedure
- [ ] The script is tested with `shellcheck` (if available) or manually reviewed for POSIX compliance

## Implementation Notes

**😴 Lazy Maintainer notes:**

- The Mac Mini runs macOS. Use `launchd` (macOS native) as an alternative to
  cron if it provides better wake-from-sleep behavior. Document both options.
- If the Mac Mini is asleep at 3 AM, the cron job won't fire. Consider
  configuring `pmset` to wake the machine at 2:55 AM, or use `launchd` which
  can fire missed jobs on wake.
- Season boundaries: MLB regular season runs April–September. The cron job
  can run year-round (off-season runs will simply find no completed games),
  or it can be disabled November–March to save resources. Document the
  trade-offs.

**🔧 Data Pipeline Janitor notes:**

- The script should check for a "lock file" to prevent overlapping runs if
  the previous night's ingestion is still running (e.g., after a long backfill).
- Log rotation: the log directory should not grow unbounded. Use `logrotate`
  or a simple age-based cleanup (delete logs older than 30 days).

**🤑 FinOps Miser notes:**

- Running on a Mac Mini that's already owned and powered on is zero
  incremental cost. This is the cheapest possible ingestion host.
- If the Mac Mini becomes unreliable, the ingestion logic is portable —
  it could run in a GitHub Actions scheduled workflow or a small EC2 instance
  as a fallback.

**🤝 API Ethicist notes:**

- The 3 AM ET schedule is intentional — it's well after the latest MLB games
  finish (typically by 1 AM ET) and before the next day's games. This avoids
  hitting the API during peak usage.
- During postseason (October), games can end later. Consider a 4 AM schedule
  during October, or simply accept that some late games may be picked up the
  following night.

This script lives in the repo's `scripts/` directory alongside existing helper
scripts. It is not a Python application — it's a shell script that invokes the
Python CLI tools.
