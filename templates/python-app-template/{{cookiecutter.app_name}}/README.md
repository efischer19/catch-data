# {{ cookiecutter.app_name }}

> {{ cookiecutter.description }}

## Installation

```bash
cd apps/{{ cookiecutter.app_name }}
poetry install
```

## Usage

```bash
poetry run {{ cookiecutter.app_name }} hello
```

## Development

```bash
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```
