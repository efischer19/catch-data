Title: feat: Create MLB API test fixtures and mocking infrastructure

## What do you want to build?

Build a comprehensive set of frozen MLB Stats API response fixtures and a shared
mocking infrastructure that all catch-data test suites can use. This enables
fast, deterministic, offline testing of the entire pipeline without hitting the
real API or AWS services.

## Acceptance Criteria

- [ ] `testing/fixtures/` contains frozen JSON files for: a full-season schedule response, at least 5 boxscore responses (covering edge cases), and at least 5 content responses
- [ ] Fixtures include edge cases: a doubleheader game, a postponed game, a game with no condensed video, a game with extra innings, a Spring Training game
- [ ] A `testing/conftest.py` provides shared pytest fixtures: `mock_mlb_client`, `mock_s3_client`, `sample_schedule`, `sample_boxscore`, `sample_content`
- [ ] The `mock_s3_client` fixture uses `moto` (AWS mock library) for realistic S3 interactions
- [ ] The `mock_mlb_client` fixture returns frozen fixture data with configurable behavior (success, 404, 500, timeout)
- [ ] All fixture data is anonymized or sourced from publicly available MLB API responses
- [ ] A README in `testing/` documents all available fixtures and their edge-case coverage
- [ ] Existing tests in `apps/catch-ingestion`, `apps/catch-processing`, and `apps/catch-analytics` can import and use these shared fixtures
- [ ] `moto` is added as a dev dependency in relevant pyproject.toml files

## Implementation Notes

**🧪 QA notes:**

- The fixture data should be captured once from the real MLB API (manually, in
  a browser or with `curl`) and then frozen. Tests must NEVER make real API
  calls. This ensures tests are fast, deterministic, and don't hit rate limits.
- Use `pytest.fixture(scope="session")` for fixture loading to avoid re-reading
  JSON files for every test.
- Consider using `pytest-recording` (VCR.py) for future integration tests that
  need realistic HTTP interaction patterns, but for V1, static fixtures are
  sufficient.

**🤝 API Ethicist notes:**

- Fixture data should be captured respectfully — a single manual session, not
  automated scraping. Document the date and source of each fixture in a
  `fixtures/README.md`.
- Do not include any personally identifiable information in fixtures. MLB
  player names and stats are public, but be cautious about any metadata that
  could be considered private.

**⚾ Baseball Edge-Case Hunter notes:**

- The fixture set should cover the most common edge cases. Suggested fixtures:
  1. `schedule_2025.json` — a typical regular season schedule
  2. `boxscore_doubleheader_g1.json` — Game 1 of a doubleheader
  3. `boxscore_doubleheader_g2.json` — Game 2 of a doubleheader
  4. `boxscore_extra_innings.json` — a game that went 12+ innings
  5. `boxscore_normal.json` — a routine 9-inning game
  6. `content_with_video.json` — game with condensed game video
  7. `content_no_video.json` — game without a condensed game video
  8. `content_postponed.json` — postponed game's content (empty/minimal)

**🔧 Data Pipeline Janitor notes:**

- The `testing/` directory is a shared test utility space per ADR-007. It is
  not a deployable package — it's imported via path dependencies in dev
  groups.
- Consider adding a `conftest.py` at the repo root that auto-discovers
  fixtures, or rely on each app's `conftest.py` importing from `testing/`.

Add `moto` and `pytest` to the shared dev dependencies. Reference ADR-004
(pytest) and ADR-007 (monorepo structure).
