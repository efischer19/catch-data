# feat: Core Web Vitals optimization and Lighthouse performance audit

## What do you want to build?

Optimize catch-app's performance to meet Core Web Vitals thresholds and achieve
a Lighthouse performance score of 95+. This includes optimizing bundle size,
reducing render-blocking resources, implementing efficient caching, and
measuring performance in CI.

## Acceptance Criteria

- [ ] Lighthouse performance score ≥ 95 on all pages (measured with throttled 4G preset)
- [ ] Largest Contentful Paint (LCP) < 2.5 seconds
- [ ] First Input Delay (FID) / Interaction to Next Paint (INP) < 200ms
- [ ] Cumulative Layout Shift (CLS) < 0.1
- [ ] First Contentful Paint (FCP) < 1.8 seconds
- [ ] Total JavaScript bundle size < 50 KB gzipped (initial load)
- [ ] No render-blocking CSS or JavaScript in the critical path
- [ ] Image assets (team logos, icons) are optimized: WebP format, proper sizing, lazy-loaded where below the fold
- [ ] A Lighthouse CI check runs on every PR and fails if scores drop below thresholds
- [ ] Performance measurements are documented in the README

## Implementation Notes

**⚡ PWA Performance Fanatic notes — this is the central performance ticket:**

- **Bundle analysis:** Use `rollup-plugin-visualizer` or `source-map-explorer`
  to identify large dependencies. The app should have very few: a router, the
  Cast SDK (async), and nothing else.
- **Code splitting:** The video player and Cast integration should be
  lazy-loaded chunks (loaded only when needed). The team selector and schedule
  views are the critical path.
- **Font optimization:** Use system fonts (`-apple-system, BlinkMacSystemFont,
  'Segoe UI', Roboto, sans-serif`) instead of web fonts. This eliminates font
  loading as a performance bottleneck.
- **JSON fetch optimization:** Gold JSON files are small and cacheable. Use
  `<link rel="preconnect">` to the CloudFront domain. Consider
  `<link rel="prefetch">` for the upcoming games JSON on the landing page.
- **Image optimization:** If team logos are used, provide them as inline SVGs
  or a CSS sprite sheet, not individual image files. This eliminates HTTP
  requests.

**Lighthouse CI setup:**

- Use `@lhci/cli` in the CI pipeline.
- Configure budgets in `lighthouserc.json`:

```json
{
  "assertions": {
    "categories:performance": ["error", {"minScore": 0.95}],
    "categories:accessibility": ["error", {"minScore": 0.90}],
    "categories:best-practices": ["error", {"minScore": 0.95}],
    "categories:pwa": ["error", {"minScore": 0.90}]
  }
}
```

**🤑 FinOps Miser notes:**

- Smaller bundles = less CDN bandwidth = lower hosting costs (already
  negligible, but good practice).
- Fast load times reduce user abandonment and improve engagement — the real
  "cost" of poor performance is user churn.

**♿ Accessibility Coordinator notes:**

- Performance optimizations must not sacrifice accessibility. Lazy-loading
  should use proper loading attributes, not JavaScript that hides content
  from screen readers.

This is a catch-app repository ticket.
