# feat: End-to-end pipeline integration tests

## What do you want to build?

Create integration tests that validate the complete data flow from Bronze
through Silver to Gold, using mocked S3 (via moto) and frozen MLB API fixtures.
These tests verify that the pipeline stages work together correctly and that
the output Gold JSON files are valid and match expected content.

## Acceptance Criteria

- [ ] An integration test ingests a frozen schedule, boxscores, and content into a mocked S3 Bronze layer
- [ ] The test invokes the Silver processing logic and verifies the `master_schedule_{year}.json` output in mocked S3
- [ ] The test invokes the Gold generation logic and verifies all 30 `team_{teamId}.json` files and `upcoming_games.json` in mocked S3
- [ ] Gold output files are validated against Gold Pydantic models
- [ ] Gold output files are validated against the generated JSON Schema (cross-validation with 02-05)
- [ ] The integration test covers the doubleheader edge case: two games for the same team on the same date appear correctly in the Gold team schedule
- [ ] The integration test covers the missing-content edge case: a game without a condensed video has `condensed_game_url: null` in Gold output
- [ ] Tests are marked with `@pytest.mark.integration` and can be run separately from unit tests
- [ ] All integration tests pass via `poetry run pytest -m integration`
- [ ] Tests complete in under 30 seconds (using mocked services, no real AWS calls)

## Implementation Notes

**🧪 QA notes:**

- These tests are the "acceptance tests" for the entire pipeline. If these
  pass, we have high confidence that nightly runs will produce correct output.
- Use `moto` to create an in-memory S3 bucket, upload Bronze fixtures, and
  then run the Silver and Gold logic in sequence. Verify the final Gold output.
- Consider using `pytest-snapshot` or `syrupy` for snapshot testing of Gold
  output files. This catches unexpected changes in the output format.

**🔧 Data Pipeline Janitor notes:**

- The integration test should simulate the full event chain: Bronze upload →
  Silver Lambda handler → Silver output → Gold Lambda handler → Gold output.
  It should NOT rely on S3 event notifications (which can't fire in moto) —
  invoke the handlers directly with simulated event payloads.
- Include a negative test: inject a malformed Bronze file and verify the
  Silver Lambda handles it gracefully (logs error, excludes bad game, still
  produces output).

**⚾ Baseball Edge-Case Hunter notes:**

- Test with a fixture schedule that includes: at least one doubleheader, one
  postponed game, one game with no content, and one extra-innings game. Verify
  each is handled correctly through the entire pipeline.

**😴 Lazy Maintainer notes:**

- These integration tests should be part of the CI pipeline so they run on
  every PR. They catch pipeline regressions before they reach production.
- If fixture data needs updating (e.g., MLB API format changes), only the
  fixture files need to change — the test logic should be stable.

Add the integration tests in a dedicated directory (e.g., `testing/integration/`)
or in each app's `tests/` directory with the `integration` marker.
Reference ADR-004 (pytest), ADR-018 (Medallion Architecture).
