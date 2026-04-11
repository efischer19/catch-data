# example-lib

> Example shared library demonstrating the monorepo library pattern.

## Purpose

This library provides a minimal example of how shared libraries work in the
monorepo. It demonstrates:

* Library structure with `pyproject.toml` and Poetry
* Snake\_case Python package naming (`example_lib`)
* Kebab-case directory naming (`example-lib`)
* Path dependency pattern for monorepo consumers
* Testing with pytest

## Installation

From an application in the monorepo, add a path dependency:

```toml
[tool.poetry.dependencies]
example-lib = { path = "../../libs/example-lib", develop = true }
```

Then install:

```bash
poetry install
```

## Usage

```python
from example_lib import greet

message = greet("World")
print(message)  # "Hello, World!"
```

## API

### `greet(name: str) -> str`

Returns a greeting message for the given name.

* **Parameters:** `name` — The name to greet
* **Returns:** A greeting string in the format `"Hello, {name}!"`

## Development

```bash
cd libs/example-lib
poetry install
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```
