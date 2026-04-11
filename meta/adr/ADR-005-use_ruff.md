---
title: "ADR-005: Use Ruff for Linting and Formatting"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "linting"
  - "formatting"
  - "core-tooling"
---

## Context

* **Problem:** The project needs consistent code style enforcement and
  static analysis across all Python applications and libraries. Historically
  this required multiple tools (flake8, black, isort, pyupgrade, etc.),
  each with its own configuration and performance characteristics.
* **Constraints:** The tooling must be fast enough to run in pre-commit
  hooks and CI without slowing down the development workflow. Configuration
  should be centralized and consistent across the monorepo.

## Decision

We will use **[Ruff](https://docs.astral.sh/ruff/)** as the single tool
for both linting and code formatting across all Python code in this
project.

Ruff replaces multiple legacy tools:

| Ruff Feature | Replaces |
| :--- | :--- |
| Linter | flake8, pylint, pyflakes, pycodestyle |
| Formatter | black |
| Import sorting | isort |
| Code upgrades | pyupgrade |

### Configuration

Ruff is configured in each project's `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"
```

### Usage

```bash
# Check for linting issues
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Check formatting without changes
ruff format --check .
```

## Considered Options

1. **Ruff (Chosen):** All-in-one linter and formatter written in Rust.
    * *Pros:* 10-100x faster than legacy tools, replaces multiple tools
      with a single binary, actively maintained, growing rule set,
      `pyproject.toml` native configuration.
    * *Cons:* Relatively new (though rapidly maturing). Does not yet cover
      every pylint rule. Formatting output may differ slightly from black
      in edge cases.
2. **flake8 + black + isort:** Traditional Python toolchain.
    * *Pros:* Battle-tested, extensive rule coverage.
    * *Cons:* Three separate tools to install, configure, and maintain.
      Slower execution, especially in CI. Configuration spread across
      multiple files.
3. **pylint:** Comprehensive static analyzer.
    * *Pros:* Deep analysis, many rules.
    * *Cons:* Very slow, complex configuration, high false-positive rate.

## Consequences

* **Positive:** One fast tool replaces an entire toolchain. Simpler
  configuration, faster CI runs, and easier onboarding for new
  contributors. Pre-commit hooks complete in seconds instead of minutes.
* **Negative:** Some niche rules from pylint or flake8 plugins may not
  have Ruff equivalents yet. Teams familiar with black/flake8 need to
  learn Ruff's configuration syntax.
* **Future Implications:** As Ruff continues to add rules and features,
  we can expand our rule selection over time.
