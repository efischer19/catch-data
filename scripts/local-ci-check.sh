#!/usr/bin/env bash
# scripts/local-ci-check.sh
#
# Run the same quality checks locally that CI runs on pull requests.
# This helps catch issues before pushing and waiting for CI feedback.
#
# Prerequisites:
#   pip install pre-commit
#   Poetry installed (https://python-poetry.org/)
#
# Usage:
#   ./scripts/local-ci-check.sh              # Run repo-wide checks only
#   ./scripts/local-ci-check.sh apps/my-app  # Also run Python checks for a project
#   ./scripts/local-ci-check.sh libs/my-lib  # Also run Python checks for a library
#
# What this script runs:
#   1. pre-commit hooks (trailing whitespace, end-of-file fixer, YAML/JSON/TOML
#      validation, merge conflict detection, mixed line endings, ADR status check,
#      ruff format, ruff lint)
#   2. Markdown linting (if markdownlint-cli2 is installed)
#   3. Python quality checks for a given app/lib directory (if specified):
#      - ruff format --check
#      - ruff check
#      - pytest
#
# To install pre-commit hooks for automatic checking on every commit:
#   pre-commit install

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_DIR="${1:-}"

echo "=== Local CI Quality Checks ==="
echo ""

# --- Pre-commit hooks ---
echo "▶ Running pre-commit hooks..."
if command -v pre-commit &> /dev/null; then
  pre-commit run --all-files
  echo "✅ Pre-commit hooks passed"
else
  echo "❌ pre-commit is not installed."
  echo "   Install it with: pip install pre-commit"
  echo "   Then run: pre-commit install"
  exit 1
fi

echo ""

# --- Markdown linting (optional) ---
echo "▶ Running markdown lint..."
if command -v markdownlint-cli2 &> /dev/null; then
  markdownlint-cli2 "**/*.md"
  echo "✅ Markdown lint passed"
elif npx --yes markdownlint-cli2 --help &> /dev/null 2>&1; then
  npx --yes markdownlint-cli2 "**/*.md"
  echo "✅ Markdown lint passed"
else
  echo "⚠️  markdownlint-cli2 is not installed — skipping markdown lint"
  echo "   Install it with: npm install -g markdownlint-cli2"
fi

echo ""

# --- Python quality checks (if a target directory is specified) ---
if [ -n "$TARGET_DIR" ]; then
  PROJECT_PATH="$REPO_ROOT/$TARGET_DIR"

  if [ ! -f "$PROJECT_PATH/pyproject.toml" ]; then
    echo "❌ No pyproject.toml found in $TARGET_DIR"
    exit 1
  fi

  echo "▶ Running Python quality checks for $TARGET_DIR..."
  cd "$PROJECT_PATH"

  echo "  ▸ poetry install..."
  poetry install --quiet

  echo "  ▸ ruff format --check..."
  poetry run ruff format --check .
  echo "  ✅ Formatting OK"

  echo "  ▸ ruff check..."
  poetry run ruff check .
  echo "  ✅ Linting OK"

  echo "  ▸ pytest..."
  poetry run pytest
  echo "  ✅ Tests passed"

  echo ""
fi

echo "=== All checks passed ✅ ==="
