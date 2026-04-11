# feat: Implement data fetching layer for Gold JSON files

## What do you want to build?

Create a typed data-fetching layer in catch-app that retrieves Gold JSON files
from the CloudFront CDN. This layer handles URL construction, HTTP fetching,
JSON parsing, type-safe deserialization, caching, and error handling for all
Gold endpoints.

## Acceptance Criteria

- [ ] A `DataService` (or similar) class/module provides typed methods: `getTeamSchedule(teamId)`, `getUpcomingGames()`
- [ ] Each method returns data typed with the generated TypeScript interfaces (e.g., `Promise<GoldTeamSchedule>`)
- [ ] The base URL for the Gold CDN is configurable via environment variable (for dev/staging/prod)
- [ ] HTTP errors (4xx, 5xx) are caught and surfaced as typed error objects, not thrown exceptions
- [ ] Network timeouts (configurable, default 10 seconds) are handled gracefully
- [ ] Responses are cached in memory for the duration of the user session (avoid re-fetching the same file)
- [ ] The `last_updated` field from the Gold JSON is exposed so the UI can display data freshness
- [ ] Unit tests mock `fetch` and verify: successful fetching, error handling, caching behavior, timeout handling
- [ ] All tests pass

## Implementation Notes

**⚡ PWA Performance Fanatic notes:**

- Use the browser's native `fetch` API — no axios or other HTTP libraries
  needed. Keeps the bundle minimal.
- Implement HTTP caching headers (`If-None-Match`, `ETag`) to leverage
  CloudFront edge caching and avoid downloading unchanged files.
- Consider using `stale-while-revalidate` pattern: show cached data
  immediately while fetching fresh data in the background. This makes the
  app feel instant even on slow connections.

**🤑 FinOps Miser notes:**

- In-memory caching means a user browsing 5 different team schedules makes 5
  fetch requests total, not 5 per page view. This reduces CloudFront request
  volume.
- Gold files are small (50-150 KB). Even without caching, bandwidth cost is
  negligible.

**♿ Accessibility Coordinator notes:**

- Loading states must be communicated to screen readers via `aria-live`
  regions or `role="status"` announcements.
- Error states should display meaningful messages, not raw HTTP codes.

**🔧 Data Pipeline Janitor notes:**

- The data layer should be completely isolated from UI components. Components
  receive data via props or hooks — they never call `fetch` directly.
- If the CDN returns a 404 (e.g., a team file doesn't exist yet), surface a
  user-friendly "Data not yet available" message rather than crashing.

This is a catch-app repository ticket.
