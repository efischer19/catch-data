---
title: "ADR-012: Use MkDocs for Documentation"
status: "Accepted"
date: "2026-03-31"
tags:
  - "documentation"
  - "python"
  - "tooling"
---

## Context

* **Problem:** The project needs a documentation system that supports
  writing documentation in Markdown, generates a browsable static site,
  and integrates with the Python ecosystem for API documentation
  generation.
* **Constraints:** The tool must be Python-native (installable via pip),
  support Markdown as the authoring format, offer a good-looking default
  theme, and support plugins for API documentation and search.

## Decision

We will use **[MkDocs](https://www.mkdocs.org/)** with the
**[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)**
theme for project documentation.

### Key Conventions

* Documentation source files live in `docs-src/` at the repository root.
* Configuration is in `mkdocs.yml` at the repository root.
* Use `mkdocstrings` for auto-generated Python API documentation.
* Build the documentation site with `mkdocs build` (output to `site/`).
* Preview locally with `mkdocs serve`.
* The `site/` directory is git-ignored; documentation is built in CI
  or on demand.

### Building Documentation

```bash
# Install documentation dependencies
pip install -r docs-requirements.txt

# Preview locally
mkdocs serve

# Build static site
mkdocs build

# Or use the provided script
./scripts/build-docs.sh
```

## Considered Options

1. **MkDocs + Material (Chosen):** Python-native documentation generator
   with Material Design theme.
    * *Pros:* Markdown authoring, beautiful Material theme, excellent
      search, Python API docs via mkdocstrings, active community,
      extensive plugin ecosystem.
    * *Cons:* Less flexible than Sphinx for complex documentation needs.
      Material theme has some features behind a sponsorship tier.
2. **Sphinx:** The traditional Python documentation tool.
    * *Pros:* Most powerful Python documentation tool, reStructuredText
      and Markdown support, extensive cross-referencing.
    * *Cons:* Steeper learning curve, reStructuredText-first design,
      configuration complexity, less modern default themes.
3. **Docusaurus:** React-based documentation platform.
    * *Pros:* Modern UI, versioning support, i18n.
    * *Cons:* Node.js dependency in a Python project, heavier build
      toolchain.

## Consequences

* **Positive:** Documentation is written in familiar Markdown. The
  Material theme provides a polished, professional appearance with
  minimal configuration. Python API docs are auto-generated from
  docstrings.
* **Negative:** Some advanced Sphinx features (complex cross-referencing,
  domain-specific directives) are not available in MkDocs.
* **Future Implications:** Documentation can be deployed to GitHub Pages
  or any static hosting platform as the project grows.
