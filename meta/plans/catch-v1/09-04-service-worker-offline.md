# feat: Implement service worker and offline caching strategy

## What do you want to build?

Add a service worker to catch-app that enables offline access to previously
viewed data and provides a reliable user experience on flaky connections. The
service worker should cache the app shell (HTML, CSS, JS) aggressively and
cache Gold JSON data with a stale-while-revalidate strategy.

## Acceptance Criteria

- [ ] A service worker is registered on first page load
- [ ] The app shell (HTML, CSS, JS bundles, icons) is precached during service worker installation
- [ ] Gold JSON files are cached on first fetch and served from cache on subsequent requests
- [ ] A stale-while-revalidate strategy is used for Gold JSON: serve cached data immediately, fetch fresh data in background
- [ ] When fully offline, the app displays previously cached team schedules and upcoming games
- [ ] When offline with no cache, the app displays a friendly "You're offline — check back when connected" message
- [ ] Cache versioning ensures stale app-shell caches are cleaned up on updates
- [ ] The service worker does NOT cache the .mp4 video URLs (these are large and hosted externally)
- [ ] A Lighthouse PWA audit scores 90+ with the service worker active
- [ ] Unit/integration tests verify: cache hit behavior, offline fallback, cache cleanup

## Implementation Notes

**📝 ADR Consideration:**

- Document the caching strategy in an ADR: which resources are precached,
  which use stale-while-revalidate, which are network-only. This is a key
  performance and UX decision.

**⚡ PWA Performance Fanatic notes:**

- Use Workbox (Google's service worker library) for reliable caching
  strategies. It's well-tested and handles edge cases (cache quotas, update
  flows, etc.).
- Precache the app shell with a version hash. When the app is updated, the
  new service worker replaces the cached shell.
- Gold JSON files should use `StaleWhileRevalidate` with a max cache age of
  24 hours. After 24 hours, the cache is considered stale and a fresh fetch
  is prioritized.
- Total cached data per user: ~5 MB (app shell) + ~5 MB (Gold JSON for
  visited teams). Well within browser cache quotas (typically 50 MB+).

**📺 Living Room Tester notes:**

- The service worker must NOT interfere with Google Cast SDK loading. Cast
  SDK scripts are loaded from Google's CDN and should use a network-first
  strategy.
- Video .mp4 URLs are hosted on MLB's CDN and are large (50-200 MB). These
  MUST NOT be cached by the service worker. Use a network-only strategy for
  any requests to MLB media domains.

**♿ Accessibility Coordinator notes:**

- When the app transitions from cached to fresh data, do not cause a jarring
  page reload. Update the content in-place and announce the update via
  `aria-live` region.
- The offline fallback page must be accessible: proper headings, readable
  text, no images that fail to load.

**🤑 FinOps Miser notes:**

- Service worker caching reduces CDN requests. Users who check scores daily
  will hit CloudFront once per day (the stale-while-revalidate refresh),
  not once per page load.

This is a catch-app repository ticket.
