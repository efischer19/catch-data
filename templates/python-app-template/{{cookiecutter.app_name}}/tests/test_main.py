"""Tests for {{ cookiecutter.app_name }} CLI."""

from click.testing import CliRunner

from {{ cookiecutter.package_name }}.main import cli


def test_cli_hello():
    """Verify the hello command runs without error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["hello"])
    assert result.exit_code == 0
    assert "Hello from {{ cookiecutter.app_name }}!" in result.output
