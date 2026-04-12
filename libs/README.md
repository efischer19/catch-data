# catch-data — Libraries

This directory contains shared libraries for **catch-data**.

## Structure

Each subdirectory represents a reusable Python library with its own
Poetry-managed dependencies:

```text
libs/
├── catch-models/
│   ├── README.md          # Library-specific documentation
│   ├── pyproject.toml     # Poetry project configuration
│   ├── catch_models/
│   │   └── ...           # Library source code
│   └── tests/             # Library tests
└── ...
```

## Conventions

* Each library lives in its own subdirectory with an independent
  `pyproject.toml`
* Every library must have a `README.md` documenting its public API, usage
  examples, and any dependencies
* Libraries should be independently testable
* Use [Poetry](../meta/adr/ADR-003-use_poetry.md) for dependency management
* Use [Ruff](../meta/adr/ADR-005-use_ruff.md) for linting and formatting
* Use [pytest](../meta/adr/ADR-004-use_pytest.md) for testing
* Follow the [Development Philosophy](../meta/DEVELOPMENT_PHILOSOPHY.md) for
  code quality standards
* Follow [Shared Library Versioning](../meta/adr/ADR-009-shared_library_versioning.md)
  conventions
* Keep libraries focused — one responsibility per library
