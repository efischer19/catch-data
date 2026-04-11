# Documentation Guide

> How to build, preview, and contribute to the project documentation using
> MkDocs.

## Overview

This project uses **[MkDocs](https://www.mkdocs.org/)** with the
**[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)**
theme to generate a static documentation site from Markdown source files in
the `docs-src/` directory.

See [ADR-012](https://github.com/{{GITHUB_OWNER}}/{{PROJECT_NAME}}/blob/main/meta/adr/ADR-012-use_mkdocs.md) for the decision record on
using MkDocs.

## Prerequisites

* Python 3.12+
* pip (or Poetry)

Install the documentation dependencies:

```bash
pip install -r docs-requirements.txt
```

## Building the Documentation

```bash
# Build the static site into the site/ directory
./scripts/build-docs.sh

# Or use MkDocs directly
mkdocs build
```

## Previewing Locally

```bash
mkdocs serve
```

Then open <http://127.0.0.1:8000> in your browser. MkDocs will live-reload
when you save changes to the source files.

## Directory Structure

```text
docs-src/
├── index.md                           # Landing page
├── CONTRIBUTING.md                    # Contributing guidelines
├── DEVELOPMENT_PHILOSOPHY.md          # Development philosophy
├── DOCUMENTATION_README.md            # This file
├── LOCAL_DEVELOPMENT_DEPENDENCIES.md  # Tool installation guide
├── SHARED_LIBRARY_VERSIONING.md       # Library versioning guide
└── FEATURE_REQUEST_AUTOMATION.md       # Feature request workflow
```

## Writing Guidelines

* Use Markdown (`.md`) for all documentation files.
* Place new files in `docs-src/` and add them to the `nav` section of
  `mkdocs.yml`.
* Follow the project's
  [markdownlint configuration](https://github.com/{{GITHUB_OWNER}}/{{PROJECT_NAME}}/blob/main/.markdownlint-cli2.yaml) for style
  consistency.
* Use admonitions (`!!! note`, `!!! warning`) for callouts.
* Use fenced code blocks with language identifiers for syntax highlighting.

## Deployment

The documentation site is built as a static site in the `site/` directory.
It can be deployed to GitHub Pages or any static hosting provider.

```bash
# Deploy to GitHub Pages (if configured)
mkdocs gh-deploy
```
