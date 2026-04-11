"""Example CLI application using Click (ADR-011)."""

import click
from example_lib import greet


@click.group()
def cli():
    """Example application CLI."""


@cli.command()
@click.option("--name", default="World", help="Name to greet.")
def hello(name: str):
    """Print a greeting message."""
    click.echo(greet(name))


if __name__ == "__main__":
    cli()
