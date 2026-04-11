Title: feat: Define Bronze layer Pydantic models for raw MLB API responses

## What do you want to build?

Create Pydantic models in `libs/catch-models` that represent the raw JSON
responses from the MLB Stats API. These models serve as the schema contract for
the Bronze layer — they validate and type the raw API payloads without
transforming them. Three model groups are needed:

1. **Schedule response** — the full-season schedule endpoint response
2. **Boxscore response** — a single game's boxscore data
3. **Content response** — a single game's editorial/media content (including
   video highlight URLs)

## Acceptance Criteria

- [ ] `catch_models/bronze.py` (or `catch_models/bronze/` subpackage) contains Pydantic v2 models for the MLB schedule API response
- [ ] Pydantic models for the boxscore API response are defined
- [ ] Pydantic models for the content/media API response are defined, including nested video `.mp4` URL fields
- [ ] All models use strict mode and forbid extra fields to catch API drift early
- [ ] Models are exported from `catch_models/__init__.py`
- [ ] Unit tests validate each model against at least two frozen API response fixtures (one typical, one edge-case)
- [ ] All tests pass via `poetry run pytest` in `libs/catch-models`

## Implementation Notes

The MLB Stats API is undocumented and its response shapes can change without
notice. Build models from real captured responses. Store frozen fixture JSON
files in `libs/catch-models/tests/fixtures/` for reproducible testing.

**⚾ Baseball Edge-Case Hunter notes:**

- Schedule responses include doubleheader games (both traditional and
  split-admission) — these have a `doubleHeader` field and `gameNumber` of 1
  or 2. The model must accommodate both.
- Postponed and suspended games have different `status.detailedState` values
  (e.g., "Postponed", "Suspended") — include these in test fixtures.
- The All-Star Game and Spring Training games may appear in schedule data. The
  model should accept them without error even if the pipeline filters them
  later.
- Games may have no content/highlights (e.g., the game just ended and no
  condensed game has been produced yet). The content model must handle missing
  or empty video arrays.

**🤝 API Ethicist notes:**

- Capture fixtures by making real API calls manually (one-time), not by
  automated scraping in tests. Tests must run against frozen fixtures only.

**🧪 QA notes:**

- Use `model_validate_json()` to test raw JSON parsing directly.
- Include a fixture for an API response with unexpected extra fields to verify
  strict validation catches drift.

Reference ADR-018 (Medallion Architecture) for the Bronze layer's role as an
immutable raw-data store with minimal validation.
