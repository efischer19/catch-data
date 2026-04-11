# feat: Scaffold catch-app TypeScript PWA with build tooling

## What do you want to build?

Initialize the `catch-app` repository as a TypeScript Progressive Web App with
modern build tooling, a `manifest.json`, and the foundational project structure.
This is the "create-react-app" (or equivalent) step that establishes the
frontend's technical foundation.

The app will be a static site with zero backend — it fetches pre-rendered JSON
files from the CloudFront CDN and renders them in the browser.

## Acceptance Criteria

- [ ] The `catch-app` repository is initialized with a TypeScript-first static site framework
- [ ] A `manifest.json` is configured with app name "Catch", theme color, icons, and `display: standalone`
- [ ] The app builds to a static `dist/` directory with `index.html`, CSS, JS bundles, and manifest
- [ ] A dev server runs locally with hot reload via `npm run dev` (or equivalent)
- [ ] The build produces optimized, minified output suitable for CDN hosting
- [ ] An initial Lighthouse audit scores 90+ on PWA category (with basic service worker placeholder)
- [ ] The project includes ESLint and Prettier configured for TypeScript
- [ ] A CI workflow runs lint, type-check, and build on every PR
- [ ] The `README.md` documents: local setup, dev server, build, and deployment
- [ ] The project uses GPL-3.0-or-later license (matching catch-data)

## Implementation Notes

**📝 ADR Consideration:**

- The PRD lists React, Vue, or Vanilla TS as framework options. This decision
  should be documented in an ADR in the catch-app repo. Recommendation:
  - **React** if component reuse and ecosystem (e.g., React Query for data
    fetching) are valued.
  - **Vue** if a lighter framework with built-in reactivity is preferred.
  - **Vanilla TS** if maximum performance and minimal bundle size are the
    priority (aligns with KISS philosophy).
- For V1 (4 simple views, no complex state), Vanilla TS with a minimal
  bundler (Vite) may be the best choice. The decision should weigh developer
  experience against simplicity.

**⚡ PWA Performance Fanatic notes:**

- Use Vite as the build tool regardless of framework choice. It provides fast
  builds, tree-shaking, and optimal code splitting out of the box.
- Set a performance budget: total initial JS bundle < 50 KB gzipped. The app
  is simple enough that this is achievable.
- Configure asset hashing for cache-busting on deployment.

**♿ Accessibility Coordinator notes:**

- Set `<html lang="en">` from the start.
- Include a skip-to-content link in the initial HTML.
- Use semantic HTML elements (`<main>`, `<nav>`, `<section>`) in the layout.

**🤑 FinOps Miser notes:**

- Hosting: GitHub Pages, Vercel, or Cloudflare Pages all offer free static
  site hosting. Choose based on custom domain support and deploy integration.
  All three have generous free tiers that this project will never exceed.

This is a catch-app repository ticket. It will be implemented in the separate
`catch-app` repo, not in `catch-data`.
