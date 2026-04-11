---
title: "ADR-011: Use Click for CLI Applications"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "cli"
  - "libraries"
---

## Context

* **Problem:** Several applications in this project expose command-line
  interfaces for operations, data processing, and administration tasks.
  We need a standard approach for building CLIs that is consistent,
  testable, and user-friendly.
* **Constraints:** The CLI framework must support nested commands (command
  groups), argument/option parsing, help text generation, input
  validation, and be easy to test programmatically.

## Decision

We will use **[Click](https://click.palletsprojects.com/)** as the
standard CLI framework for all Python command-line applications.

### Key Conventions

* Use Click's decorator-based API for defining commands and options.
* Organize complex CLIs using **command groups** for related
  subcommands.
* Use `click.testing.CliRunner` for testing CLI commands without
  spawning subprocesses.
* Provide `--help` documentation for all commands and options.
* Use Click's type system for input validation (e.g., `click.Path`,
  `click.Choice`, `click.IntRange`).

### Example

```python
import click

@click.group()
def cli():
    """My application CLI."""

@cli.command()
@click.option("--name", required=True, help="Name to greet")
@click.option("--count", default=1, help="Number of greetings")
def greet(name: str, count: int):
    """Greet someone by name."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")

if __name__ == "__main__":
    cli()
```

### Testing Example

```python
from click.testing import CliRunner
from myapp.cli import cli

def test_greet():
    runner = CliRunner()
    result = runner.invoke(cli, ["greet", "--name", "World"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output
```

## Considered Options

1. **Click (Chosen):** Composable CLI framework with decorator syntax.
    * *Pros:* Clean decorator API, command groups for complex CLIs,
      built-in testing utilities (`CliRunner`), automatic help
      generation, excellent documentation, widely adopted.
    * *Cons:* External dependency. Decorator-based API differs from
      argparse patterns.
2. **argparse:** Python standard library argument parser.
    * *Pros:* No external dependency, well-documented.
    * *Cons:* Verbose for complex CLIs, no built-in command groups
      (subparsers are awkward), harder to test, no automatic help
      formatting.
3. **Typer:** Modern CLI framework built on Click and type hints.
    * *Pros:* Type-hint based API, less boilerplate than Click.
    * *Cons:* Adds a layer of abstraction over Click. May have
      limitations for complex CLI patterns. Click knowledge is still
      needed for advanced features.
4. **Fire:** Automatic CLI generation from Python objects.
    * *Pros:* Zero boilerplate, generates CLI from any function/class.
    * *Cons:* Less control over CLI behavior, poor help text generation,
      harder to validate inputs.

## Consequences

* **Positive:** Consistent CLI patterns across all applications. Easy
  to test with `CliRunner`. Users get automatic `--help` documentation.
  Command groups scale well for complex applications.
* **Negative:** Click must be added as a dependency. Contributors
  unfamiliar with Click's decorator patterns need brief onboarding.
* **Future Implications:** Click integrates well with other libraries
  in the ecosystem (e.g., Rich for enhanced output formatting).
