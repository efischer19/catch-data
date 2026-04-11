# feat: Implement Gold layer upcoming games JSON generation

## What do you want to build?

Add logic to the Gold layer Lambda in `apps/catch-analytics` that produces
`gold/upcoming_games.json` — a consolidated view of recently completed and
upcoming games across all MLB teams. This is the "Today's Slate" data source
for the catch-app frontend.

## Acceptance Criteria

- [ ] The Lambda produces `gold/upcoming_games.json` containing games within a rolling window (e.g., 1 day ago through 7 days ahead)
- [ ] The file includes both recently completed games (with scores) and upcoming scheduled games
- [ ] Games are sorted by date and start time ascending
- [ ] The output conforms to the `GoldUpcomingGames` Pydantic model
- [ ] The rolling window boundaries are configurable via environment variables (default: 1 day back, 7 days forward)
- [ ] The `last_updated` timestamp reflects when the file was generated
- [ ] Games are grouped by date for easy frontend rendering
- [ ] Unit tests verify: window filtering, sort order, date grouping, boundary edge cases (no games today, end of season)
- [ ] All tests pass via `poetry run pytest` in `apps/catch-analytics`

## Implementation Notes

**⚾ Baseball Edge-Case Hunter notes:**

- **All-Star Break:** During the 4-day All-Star break (mid-July), there are
  no regular-season games. The upcoming games file should be empty or contain
  only the All-Star Game itself. The frontend should handle an empty list
  gracefully (show "No games scheduled").
- **End of regular season:** In late September/early October, the schedule
  transitions to postseason. Games with `game_type != "R"` should be included
  in the upcoming view (postseason is exciting!).
- **Rain delays / postponements:** A game postponed today may not appear as
  "scheduled" for today anymore. It should appear on its rescheduled date.
- **Doubleheaders:** Two games on the same date for the same teams should
  both appear, clearly identified as Game 1 and Game 2.
- **Off days:** Not every team plays every day. The upcoming view may have
  fewer than 15 games on a given date.

**⚡ PWA Performance Fanatic notes:**

- The upcoming games file covers ~8 days of games. At ~15 games/day, this is
  ~120 games. With minimal fields per game, this should be under 30 KB — fast
  to fetch on any connection.
- The 1-day lookback ensures that yesterday's scores are available for users
  checking in the morning. Increase to 2 days if user testing shows demand.

**🤑 FinOps Miser notes:**

- One additional S3 PUT per night for this file. Negligible cost.
- The rolling window keeps the file small. A full-season file would be much
  larger and wasteful for the "today's slate" use case.

**😴 Lazy Maintainer notes:**

- The window is date-based, not relative to "today" at the time the user
  loads the page. The file is regenerated nightly, so "today" in the file
  corresponds to the day the pipeline ran. This is acceptable for V1 (nightly
  updates, not real-time).
- Consider whether the window should be extended at the end of the season to
  include postseason results for longer viewing.
