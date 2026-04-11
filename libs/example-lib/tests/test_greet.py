"""Tests for the greet module."""

from example_lib import greet


def test_greet_returns_greeting():
    """Verify greet returns the expected greeting string."""
    assert greet("World") == "Hello, World!"


def test_greet_with_different_name():
    """Verify greet works with various names."""
    assert greet("Python") == "Hello, Python!"
