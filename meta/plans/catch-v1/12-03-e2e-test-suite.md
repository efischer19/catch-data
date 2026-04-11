# feat: End-to-end and visual regression test suite for catch-app

## What do you want to build?

Build a comprehensive automated test suite for catch-app that covers unit tests,
integration tests, and end-to-end (E2E) tests. The test suite should provide
high confidence that the app works correctly across views and interactions, and
should catch visual regressions automatically.

## Acceptance Criteria

- [ ] Unit tests cover: data fetching layer, data transformation/formatting utilities, team list constant validation
- [ ] Component tests cover: team selector rendering, schedule view rendering with mock data, boxscore view rendering, video player controls
- [ ] E2E tests cover the critical user paths: open app → view today's slate → select a team → view schedule → open boxscore → play video
- [ ] E2E tests use a test framework (e.g., Playwright, Cypress) with mocked Gold JSON responses (no real CDN dependency)
- [ ] Visual regression tests capture screenshots of key views and compare against baseline snapshots
- [ ] All tests run in CI on every PR
- [ ] Test coverage report is generated and accessible (not gated on a specific percentage, but tracked)
- [ ] Tests complete in under 2 minutes in CI
- [ ] A testing README documents: how to run tests locally, how to update visual snapshots, how to add new E2E scenarios

## Implementation Notes

**🧪 QA-for-the-Future Fanatic notes — this is the central testing ticket:**

- **Unit tests:** Use the framework's native testing tools (e.g., Vitest for
  Vite projects). Test pure functions: date formatting, score display
  formatting, timezone conversion, team lookup by ID.
- **Component tests:** Use Testing Library (`@testing-library/dom` or
  framework-specific variant) for component-level tests. Test that components
  render correctly with mock data and respond to user interactions.
- **E2E tests:** Use Playwright for cross-browser E2E testing. Playwright
  supports Chrome, Firefox, and Safari — critical for a PWA.
- **Visual regression:** Use Playwright's built-in screenshot comparison or
  a tool like Percy/Chromatic. Start with Playwright screenshots (free,
  no external service).

**Mock data strategy:**

- E2E tests should intercept `fetch` requests and return mock Gold JSON
  responses. This makes tests fast, deterministic, and independent of the
  data pipeline.
- Use the same JSON Schema from catch-data to validate mock data, ensuring
  test fixtures are realistic.

**⚾ Baseball Edge-Case Hunter notes:**

- Include E2E scenarios for:
  1. A team schedule with a doubleheader
  2. Today's slate with no games (All-Star break)
  3. A boxscore with no save
  4. A game with no condensed video
  5. A postponed game in the schedule

**♿ Accessibility Coordinator notes:**

- Integrate `axe-core` into E2E tests. Run an accessibility scan on each page
  visited during E2E scenarios. This catches regressions automatically.

**😴 Lazy Maintainer notes:**

- Visual regression baselines should be updated intentionally (via a commit),
  not automatically. This forces a human review of visual changes.
- E2E tests with mocked data don't break when the pipeline changes — they
  only break when the frontend code changes. This reduces false positives.

This is a catch-app repository ticket.
