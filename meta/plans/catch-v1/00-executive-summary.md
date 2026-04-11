# Catch V1 — Executive Summary

> Planning document for the Catch App V1 initiative, covering both the
> `catch-data` (backend/data) and `catch-app` (frontend/UI) repositories.

## Vision

Catch is a zero-to-low-cost Progressive Web App that lets users browse MLB
schedules, view boxscores, and cast condensed-game highlight videos to Google
Cast devices. The system uses a serverless, static JAMstack architecture with a
GitOps-driven, two-repository design.

## Architecture Overview

| Component | Repository | Technology |
|---|---|---|
| Data ingestion (Bronze) | catch-data | Python CLI on Mac Mini |
| Data processing (Silver) | catch-data | AWS Lambda |
| Data serving (Gold) | catch-data | AWS Lambda → S3 + CloudFront |
| Schema sync | catch-data → catch-app | GitHub Actions |
| Frontend PWA | catch-app | TypeScript static app |

Data flows through an S3 Medallion Architecture (ADR-018):

```text
Mac Mini cron ──► Bronze (raw API JSON)
                      │
               S3 event trigger
                      ▼
                Silver Lambda (cleaned, joined)
                      │
               S3 event trigger
                      ▼
                Gold Lambda (UI-ready JSON)
                      │
               CloudFront CDN
                      ▼
                catch-app PWA
```

## Epics & Sequencing

### Phase 1 — Foundation (catch-data)

| Epic | Tickets | Dependencies | Summary |
|---|---|---|---|
| **1: Project Bootstrap** | 01-01 through 01-04 | None | License change, placeholder replacement, rename example apps/libs, update CI |
| **2: Shared Data Models** | 02-01 through 02-05 | Epic 1 | Pydantic models for all three medallion layers, S3 path conventions, JSON Schema generation |
| **6: Infrastructure** | 06-01 through 06-04 | Epic 1 | Terraform for S3, Lambda, CloudFront, IAM (can run in parallel with Epic 2) |

### Phase 2 — Pipeline (catch-data)

| Epic | Tickets | Dependencies | Summary |
|---|---|---|---|
| **3: Bronze Ingestion** | 03-01 through 03-05 | Epics 2, 6 | MLB API client, schedule/boxscore/content ingestion, cron setup |
| **4: Silver Processing** | 04-01 through 04-03 | Epics 2, 3, 6 | Lambda to clean and join data, S3 event triggers, error handling |
| **5: Gold Serving** | 05-01 through 05-03 | Epics 2, 4, 6 | Team schedule and upcoming games generation, validation |

### Phase 3 — Integration (catch-data + catch-app)

| Epic | Tickets | Dependencies | Summary |
|---|---|---|---|
| **7: Schema Sync** | 07-01 through 07-02 | Epic 2 | JSON Schema generation Action, cross-repo PR automation |
| **8: Testing & Observability** | 08-01 through 08-03 | Epics 3, 4, 5 | API mocks, integration tests, pipeline monitoring |

### Phase 4 — Frontend (catch-app)

| Epic | Tickets | Dependencies | Summary |
|---|---|---|---|
| **9: PWA Foundation** | 09-01 through 09-04 | Epic 7 | TypeScript scaffold, schema types, data fetching, service worker |
| **10: Core UI** | 10-01 through 10-04 | Epic 9 | Team selector, schedule view, today's slate, boxscore |
| **11: Media & Casting** | 11-01 through 11-02 | Epic 10 | Video player, Google Cast integration |
| **12: Quality & Accessibility** | 12-01 through 12-03 | Epics 10, 11 | WCAG, Core Web Vitals, E2E tests |

## Persona Review Summary

Each ticket has been reviewed through the following lenses:

| Persona | Key Concerns Addressed |
|---|---|
| 🤑 **FinOps Miser** | Lambda memory/timeout tuning, S3 lifecycle policies, CloudFront caching, no always-on compute |
| ⚾ **Baseball Edge-Case Hunter** | Doubleheaders, rainouts, postponements, suspended games, All-Star break, no-condensed-game scenarios |
| 🔧 **Data Pipeline Janitor** | Strict Bronze→Silver→Gold separation, dead-letter handling, idempotent writes, data quality gates |
| 😴 **Lazy Maintainer** | Zero manual maintenance, season rollover automation, self-healing retries, automated schema sync |
| 📺 **Living Room Tester** | Cast SDK Default Media Receiver, .mp4 URL validation, fallback to browser playback |
| ⚡ **PWA Performance Fanatic** | Static JSON fetches, service worker caching, code splitting, Core Web Vitals targets |
| 🤝 **Unofficial API Ethicist** | Honest User-Agent, rate limiting, robots.txt compliance, minimal fetching, aggressive caching |
| ♿ **Accessibility Coordinator** | WCAG 2.1 AA, semantic HTML, keyboard navigation, screen reader testing, color contrast |
| 🧪 **QA-for-the-Future Fanatic** | Frozen API fixtures, contract tests, integration tests, E2E coverage, CI gates |

## ADR Decisions Needed

Several tickets flag new architectural decisions that should be documented as ADRs:

| Ticket | Proposed ADR Topic |
|---|---|
| 02-05 | Schema-driven development and JSON Schema generation strategy |
| 03-01 | User-Agent policy for MLB Stats API (ROBOT_ETHICS.md vs PRD conflict) |
| 06-03 | CloudFront distribution and CORS policy for gold layer |
| 07-02 | Cross-repo automation strategy and permissions model |
| 09-01 | Frontend framework selection (React/Vue/Vanilla TS) |
| 09-04 | Service worker caching strategy for gold JSON files |

## Ticket Count

| Scope | Epics | Tickets |
|---|---|---|
| catch-data | 8 | 29 |
| catch-app | 4 | 13 |
| **Total** | **12** | **42** |
