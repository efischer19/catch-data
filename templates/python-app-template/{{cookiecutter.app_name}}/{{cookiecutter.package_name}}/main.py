"""CLI entry point for {{ cookiecutter.app_name }}."""

import click


@click.group()
def cli():
    """{{ cookiecutter.app_name }} CLI."""


@cli.command()
def hello():
    """Print a hello message."""
    click.echo("Hello from {{ cookiecutter.app_name }}!")


if __name__ == "__main__":
    cli()
