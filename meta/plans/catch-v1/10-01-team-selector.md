# feat: Implement team selector and app navigation

## What do you want to build?

Build the primary navigation for catch-app: a team selector that lets users pick
one of the 30 MLB teams to view their schedule, plus top-level navigation
between the "Team Schedule" and "Today's Slate" views. The team list is static
(hardcoded) — it does not require an API call.

## Acceptance Criteria

- [ ] A team selector displays all 30 MLB teams, organized by league (AL/NL) and division (East/Central/West)
- [ ] Each team entry shows the team name and abbreviation
- [ ] Selecting a team navigates to the team schedule view (`/team/{teamId}`)
- [ ] A top-level navigation bar provides links to "Today's Slate" (`/`) and "Teams" (`/teams`)
- [ ] The currently selected team is visually highlighted in the team list
- [ ] Navigation uses client-side routing (no full page reloads)
- [ ] The team list data is hardcoded as a static TypeScript constant (30 teams × id, name, abbreviation, league, division)
- [ ] The team selector is keyboard-navigable (arrow keys to move, Enter to select)
- [ ] The team selector works correctly on mobile viewport sizes (responsive layout)
- [ ] The URL is bookmarkable: navigating to `/team/147` directly loads the Yankees schedule

## Implementation Notes

**♿ Accessibility Coordinator notes:**

- The team selector should use semantic HTML: `<nav>` for navigation, `<ul>`
  and `<li>` for the team list, `<a>` or `<button>` for team entries.
- Each team entry should have an accessible label: `aria-label="New York
  Yankees"` (or the visible text is sufficient if it includes the full name).
- The navigation bar should use `<nav aria-label="Main navigation">`.
- Focus management: when the user selects a team and navigates to the
  schedule view, move focus to the main content area heading.

**⚡ PWA Performance Fanatic notes:**

- The team list is static — no network request needed. The selector should
  render instantly.
- Use client-side routing (e.g., History API, or framework router) to avoid
  full page reloads. Transitions should feel instant.

**⚾ Baseball Edge-Case Hunter notes:**

- The 30-team list has been stable since 2005 (when the Expos became the
  Nationals). Hardcoding is safe for V1.
- If a team relocates (historically rare), updating the static list is a
  one-line code change — no architecture change needed.
- Team IDs in the MLB API are stable integers. Use these as the canonical
  identifier.

**📺 Living Room Tester notes:**

- On larger screens (TV/monitor via Cast), the team selector should be
  usable with simple up/down/select controls (d-pad friendly). Ensure focus
  states are large and visible.

This is a catch-app repository ticket.
