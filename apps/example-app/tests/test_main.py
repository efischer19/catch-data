"""Tests for the example-app CLI."""

from click.testing import CliRunner

from app.main import cli


def test_cli_hello_default():
    """Verify the hello command runs without error using the default name."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output


def test_cli_hello_with_name():
    """Verify the hello command greets a specified name."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hello", "--name", "Python"])
    assert result.exit_code == 0
    assert "Hello, Python!" in result.output
