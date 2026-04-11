# example-app

> Example application demonstrating the monorepo app pattern.

## Purpose

This application provides a minimal example of how applications work in the
monorepo. It demonstrates:

* Application structure with `pyproject.toml` and Poetry
* Click-based CLI (per [ADR-011](../../meta/adr/ADR-011-use_click.md))
* Path dependency on a shared library (`example-lib`)
* Testing CLI commands with `click.testing.CliRunner`

## Installation

```bash
cd apps/example-app
poetry install
```

## Usage

```bash
# Run the CLI
poetry run example-app hello
# Output: Hello, World!

poetry run example-app hello --name Python
# Output: Hello, Python!
```

## Development

```bash
cd apps/example-app
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```

## Dependencies

* **[example-lib](../../libs/example-lib/)** — Shared greeting library
  (path dependency)
* **[Click](https://click.palletsprojects.com/)** — CLI framework
  (see [ADR-011](../../meta/adr/ADR-011-use_click.md))
