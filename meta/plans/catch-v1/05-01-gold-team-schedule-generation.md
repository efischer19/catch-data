Title: feat: Implement Gold layer team schedule JSON generation

## What do you want to build?

Build the Lambda logic in `apps/catch-analytics` that reads the Silver
`master_schedule_{year}.json` and produces 30 individual team schedule files:
`gold/team_{teamId}.json`. Each file contains that team's full season schedule
in the `GoldTeamSchedule` Pydantic model format, optimized for direct frontend
consumption.

## Acceptance Criteria

- [ ] The Lambda reads `silver/master_schedule_{year}.json` and deserializes it into a `SilverMasterSchedule` model
- [ ] For each of the 30 MLB teams, the Lambda filters games where the team is home or away
- [ ] Each team's games are sorted by date ascending
- [ ] The output for each team is serialized as a `GoldTeamSchedule` model and written to `gold/team_{teamId}.json`
- [ ] The `GoldTeamSchedule` includes team metadata: `team_id`, `team_name`, `team_abbreviation`, `season_year`, `last_updated`
- [ ] Completed games include score, boxscore summary, and condensed game URL (if available)
- [ ] Future/scheduled games include date, opponent, venue, and start time only
- [ ] Pydantic validation is applied to each output file before writing to S3
- [ ] All 30 files are written in a single Lambda invocation
- [ ] Unit tests verify: correct filtering by team, sort order, Gold model compliance, handling of teams with doubleheader games
- [ ] All tests pass via `poetry run pytest` in `apps/catch-analytics`

## Implementation Notes

**The 30 MLB teams** have stable `teamId` values that rarely change. Hardcode
the team list as a constant in `catch_models` (or fetch from the schedule data
dynamically). Current team IDs range from 108 (LAA) to 147 (NYY).

**⚡ PWA Performance Fanatic notes:**

- Each team file should be as small as possible. A 162-game schedule with
  boxscore summaries is typically 50-150 KB of JSON. This is well within
  acceptable PWA payload sizes.
- Use `model_dump(mode="json", exclude_none=True)` to omit null fields and
  reduce file size.

**⚾ Baseball Edge-Case Hunter notes:**

- **Doubleheaders:** A team may have two games on the same date. Both should
  appear in the schedule with `game_number` set to 1 and 2.
- **Traded players in boxscores:** A player may appear in the boxscore for
  both teams across a season (traded mid-season). This is fine — boxscore
  data is per-game, not aggregated.
- **Teams changing names/locations (extremely rare):** The `team_name` and
  `team_abbreviation` should come from the Silver data for that specific game,
  not a hardcoded lookup. This future-proofs against the unlikely-but-possible
  team relocation scenario.

**🔧 Data Pipeline Janitor notes:**

- The Lambda writes all 30 files atomically in one invocation. If the Lambda
  fails mid-write, some files may be updated while others are stale. This is
  acceptable for V1 — CloudFront caching smooths over brief inconsistencies.
  A future improvement could use S3 batch operations.
- If a team has zero games in the schedule (e.g., early in the season before
  their first game), still write an empty `GoldTeamSchedule` file so the
  frontend doesn't get a 404.

**🤑 FinOps Miser notes:**

- 30 S3 PUTs per nightly run = 30 × 365 = 10,950 PUTs/year ≈ $0.06/year.
- Total Gold layer storage: 30 files × 150 KB = ~4.5 MB. Negligible cost.
