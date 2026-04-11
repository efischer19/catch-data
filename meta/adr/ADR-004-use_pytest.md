---
title: "ADR-004: Use pytest for Testing"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "testing"
  - "core-tooling"
---

## Context

* **Problem:** The project needs a standardized testing framework that
  supports clear, maintainable tests across all applications and libraries.
  The testing approach should support fixtures, parameterization, and
  plugin extensibility.
* **Constraints:** The framework must work well with Poetry, integrate
  easily with CI/CD pipelines, and support both unit and integration
  testing patterns.

## Decision

We will use **[pytest](https://docs.pytest.org/)** as the testing framework
for all Python applications and libraries in this project.

### Key Conventions

* Tests live in a `tests/` directory within each application or library.
* Shared test utilities and fixtures live in the top-level `testing/`
  directory.
* Use `conftest.py` files for fixtures scoped to a directory.
* Test files follow the naming pattern `test_<module>.py`.
* Test functions follow the naming pattern `test_<behavior>`.
* Use `pytest.mark.parametrize` for data-driven tests.
* Use `pytest-cov` for coverage reporting when needed.

### Running Tests

```bash
# Run all tests in a project
cd apps/<app-name>
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=src
```

## Considered Options

1. **pytest (Chosen):** Feature-rich testing framework with excellent
   plugin ecosystem.
    * *Pros:* Simple assertion syntax (plain `assert`), powerful fixture
      system, extensive plugin ecosystem (cov, mock, asyncio, etc.),
      parameterized tests, excellent error reporting.
    * *Cons:* Additional dependency (not part of stdlib). Fixture
      injection via function arguments can be non-obvious to newcomers.
2. **unittest:** Python standard library testing framework.
    * *Pros:* No additional dependencies, familiar to Java/JUnit users.
    * *Cons:* Verbose class-based syntax, weaker assertion introspection,
      limited parameterization support, no built-in fixture system.
3. **nose2:** Successor to nose.
    * *Pros:* unittest-compatible, plugin support.
    * *Cons:* Smaller community, fewer plugins, less active development
      compared to pytest.

## Consequences

* **Positive:** Clean, readable tests with minimal boilerplate. Rich
  ecosystem of plugins for coverage, mocking, async testing, and more.
  Excellent integration with IDEs and CI/CD systems.
* **Negative:** pytest must be added as a development dependency to each
  project. Contributors unfamiliar with pytest fixtures may need a brief
  onboarding.
* **Future Implications:** The `testing/` directory provides a natural
  home for shared fixtures and test factories as the project grows.
