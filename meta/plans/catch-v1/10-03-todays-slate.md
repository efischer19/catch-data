# feat: Implement today's slate (upcoming games) view

## What do you want to build?

Build the "Today's Slate" view — the app's landing page — that displays a
consolidated list of all MLB games happening today and in the near future. This
view fetches `gold/upcoming_games.json` from the CDN and renders games grouped
by date, showing matchups, times, and scores for completed games.

## Acceptance Criteria

- [ ] The today's slate view loads and displays data from `gold/upcoming_games.json`
- [ ] Games are grouped by date with clear date headers (e.g., "Thursday, July 10, 2025")
- [ ] Today's games are visually emphasized (highlighted section, larger text, or distinct styling)
- [ ] Each game shows: away team @ home team, start time or final score, status
- [ ] Completed games show the final score and a "Boxscore" link
- [ ] Completed games with condensed game videos show a "Watch" button
- [ ] Scheduled games show the start time in the user's local timezone
- [ ] The view handles an empty state gracefully (e.g., All-Star break: "No games scheduled today")
- [ ] A loading indicator displays while the data is being fetched
- [ ] The `last_updated` timestamp is displayed to set user expectations about data freshness
- [ ] The view is responsive and optimized for quick scanning on mobile

## Implementation Notes

**⚾ Baseball Edge-Case Hunter notes:**

- **All-Star Break:** 4 days in mid-July with no regular-season games. The
  view should show a friendly empty state, not an error.
- **Doubleheaders:** Two games between the same teams on the same date should
  both appear, labeled "Game 1" and "Game 2".
- **Time zones:** The Gold data stores UTC timestamps. The frontend must
  convert to the user's local timezone for start times. Use
  `Intl.DateTimeFormat` for localization.
- **Late games still in progress:** If a game started at 10 PM ET and the
  nightly pipeline ran at 3 AM ET, the game may show "In Progress" with no
  final score. Display the status clearly.
- **Rain delays:** A game in rain delay may show "Delayed" status. Handle
  this as a variant of "In Progress".

**♿ Accessibility Coordinator notes:**

- Date group headings should use `<h2>` or `<h3>` elements, not just styled
  `<div>` elements.
- The game list should be navigable by keyboard: Tab to move between games,
  Enter to view boxscore.
- Today's section should be announced by screen readers: consider using
  `aria-current="date"` on today's heading.
- Timezone handling: display the timezone name (e.g., "7:10 PM ET") so users
  know which timezone is shown.

**⚡ PWA Performance Fanatic notes:**

- This is the app's landing page — it must load fast. Target: First
  Contentful Paint < 1 second on a 4G connection.
- The `upcoming_games.json` file is small (~30 KB for an 8-day window). It
  should load in a single fetch with no pagination needed.
- Consider pre-fetching team schedule data for teams that appear in today's
  slate, so that navigating to a team schedule feels instant.

This is a catch-app repository ticket.
