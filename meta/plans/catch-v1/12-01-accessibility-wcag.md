# feat: WCAG 2.1 AA accessibility compliance and testing

## What do you want to build?

Conduct a comprehensive accessibility audit of catch-app and remediate any
issues to achieve WCAG 2.1 Level AA compliance. This includes automated
accessibility testing in CI, manual screen reader testing, and keyboard
navigation verification across all views.

## Acceptance Criteria

- [ ] An automated accessibility testing tool (e.g., `axe-core`, `pa11y`) is integrated into the CI pipeline
- [ ] Zero critical or serious accessibility violations in automated scans across all views
- [ ] All interactive elements are reachable and operable via keyboard alone (no mouse required)
- [ ] Focus order follows a logical reading sequence on all pages
- [ ] All images and icons have appropriate alt text or `aria-label`
- [ ] Color contrast meets WCAG AA minimum: 4.5:1 for normal text, 3:1 for large text
- [ ] Form controls (team selector, search if present) have associated labels
- [ ] The app is tested with at least two screen readers: VoiceOver (macOS/iOS) and NVDA (Windows)
- [ ] A skip-to-content link is present and functional on every page
- [ ] Reduced motion preference (`prefers-reduced-motion`) is respected for any animations
- [ ] An accessibility statement page documents compliance level and known limitations

## Implementation Notes

**♿ Accessibility Coordinator notes — this is the central accessibility ticket:**

- Use `axe-core` (via `@axe-core/playwright` or `jest-axe`) for automated
  testing. It catches ~57% of WCAG issues automatically.
- Manual testing is required for the remaining issues that automated tools
  can't catch: reading order, focus management, screen reader announcements.
- **Screen reader test script:** Create a brief manual test checklist:
  1. Navigate to Today's Slate with VoiceOver. Can you hear all game matchups?
  2. Select a team from the team selector. Is the selection announced?
  3. Open a boxscore. Can you hear the R/H/E data meaningfully?
  4. Open the video player. Can you start, pause, and close the player?
  5. Start a Cast session. Is the state change announced?
- Store the test checklist in the repo as a manual QA document.

**⚡ PWA Performance Fanatic notes:**

- Accessibility and performance are complementary, not conflicting. Semantic
  HTML is faster to parse, proper headings help with SEO, and keyboard
  navigation requires no additional JavaScript.

**🧪 QA notes:**

- Add accessibility tests to the CI pipeline so they run on every PR. Use
  `axe-core` programmatically in test files, not just as a browser extension.
- Consider using `pa11y-ci` for page-level automated audits as a CI check.
- Track accessibility regressions: if a new component is added without proper
  accessibility, the CI should fail.

This is a catch-app repository ticket.
