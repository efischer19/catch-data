# catch-data — Testing

This directory contains shared testing utilities and fixtures for
**catch-data**.

## Purpose

The `testing/` directory provides reusable test infrastructure that can be
shared across multiple applications and libraries in the monorepo. This
avoids duplicating common test helpers and promotes consistent testing
patterns.

## Structure

```text
testing/
├── README.md              # This file
├── __init__.py            # Allows shared fixture imports
├── conftest.py            # Shared pytest fixtures
├── fixtures/              # Frozen MLB Stats API response fixtures
├── factories/             # Test data factories
└── helpers/               # Shared test utility functions
```

## Conventions

* Shared fixtures and helpers live here; application-specific tests stay in
  their respective `tests/` directories
* Follow the [Development Philosophy](../meta/DEVELOPMENT_PHILOSOPHY.md) for
  testing standards
* Use pytest as the test framework
  (see [ADR-004](../meta/adr/ADR-004-use_pytest.md))
* Keep test utilities focused and well-documented

## Shared Fixtures

`testing/conftest.py` now provides shared pytest fixtures for all apps:

* `mock_mlb_client` — configurable frozen MLB API client
  (`success`, `404`, `500`, `timeout`)
* `mock_s3_client` — moto-backed boto3 S3 client with a pre-created
  `catch-data-test-bucket`
* `sample_schedule` — `testing/fixtures/schedule_2025.json`
* `sample_boxscore` — `testing/fixtures/boxscore_normal.json`
* `sample_content` — `testing/fixtures/content_with_video.json`

See [`testing/fixtures/README.md`](./fixtures/README.md) for the full fixture
catalog, source notes, and edge-case coverage.
