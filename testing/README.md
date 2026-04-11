# {{PROJECT_NAME}} — Testing

This directory contains shared testing utilities and fixtures for
**{{PROJECT_NAME}}**.

## Purpose

The `testing/` directory provides reusable test infrastructure that can be
shared across multiple applications and libraries in the monorepo. This
avoids duplicating common test helpers and promotes consistent testing
patterns.

## Structure

```text
testing/
├── README.md              # This file
├── conftest.py            # Shared pytest fixtures (if applicable)
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
