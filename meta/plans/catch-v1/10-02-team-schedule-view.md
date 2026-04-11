# feat: Implement team schedule view

## What do you want to build?

Build the team schedule page that displays a selected team's full-season
schedule. The view fetches `gold/team_{teamId}.json` from the CDN and renders
each game as a list/card showing date, opponent, score (if completed), status,
and a link to the boxscore or "Watch Condensed Game" action.

## Acceptance Criteria

- [ ] The team schedule view loads and displays data from `gold/team_{teamId}.json`
- [ ] Each game shows: date, home/away indicator, opponent name, start time (for scheduled games), final score (for completed games)
- [ ] Completed games show a "Boxscore" link/button that navigates to the boxscore view
- [ ] Completed games with a condensed game URL show a "Watch Condensed Game" button
- [ ] Scheduled/future games show "Scheduled" status with start time
- [ ] Postponed games show "Postponed" status with appropriate styling
- [ ] The schedule is displayed in chronological order with month/date grouping
- [ ] A loading indicator displays while the Gold JSON is being fetched
- [ ] An error state displays if the fetch fails, with a retry button
- [ ] The `last_updated` timestamp is displayed at the bottom of the page
- [ ] The view is responsive: card layout on mobile, table layout on desktop

## Implementation Notes

**⚾ Baseball Edge-Case Hunter notes:**

- **Doubleheaders:** Two games on the same date should be clearly labeled
  "Game 1" and "Game 2". Do not collapse them into a single row.
- **Today's game:** If the team is playing today and the game is in progress
  (status: "In Progress"), display the status but note that the score is from
  the last nightly update, not live. Consider a "Score from last update" label.
- **Off days:** Days with no game should NOT be shown (don't render 365 rows
  for 162 games). Only show actual game dates.
- **Spring Training games:** If present in the Gold data, either filter them
  out or display them in a separate section. The Gold layer should ideally
  filter them, but the frontend should be defensive.

**♿ Accessibility Coordinator notes:**

- Use a `<table>` element for the desktop layout with proper `<thead>`,
  `<th>`, and `<td>` elements. Tables are well-supported by screen readers.
- For the mobile card layout, use `<article>` elements with accessible
  headings for each game.
- Loading state: use `aria-busy="true"` on the content region during fetch.
- Score display should be readable: "Yankees 5, Red Sox 3" not just "5-3"
  (provide both visual and accessible versions).

**⚡ PWA Performance Fanatic notes:**

- Team schedule JSON is typically 50-150 KB. With service worker caching,
  returning users see cached data instantly while fresh data loads in the
  background.
- Consider lazy-loading past months: show the current month by default and
  load earlier months on scroll/expand. This reduces initial render time.

This is a catch-app repository ticket.
