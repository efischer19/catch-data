# {{ cookiecutter.lib_name }}

> {{ cookiecutter.description }}

## Installation

Add a path dependency from your application:

```toml
[tool.poetry.dependencies]
{{ cookiecutter.lib_name }} = { path = "../../libs/{{ cookiecutter.lib_name }}", develop = true }
```

## Development

```bash
cd libs/{{ cookiecutter.lib_name }}
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```
