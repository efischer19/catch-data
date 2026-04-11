---
title: "ADR-002: Use Python 3.12+"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "runtime"
  - "core-tooling"
---

## Context

* **Problem:** The project needs a standardized Python version that all
  applications and libraries target. Choosing a minimum Python version
  affects which language features, performance optimizations, and
  third-party libraries are available.
* **Constraints:** The chosen version must be actively supported by the
  Python Software Foundation, have broad ecosystem compatibility, and
  provide modern language features that improve developer productivity.

## Decision

We will use **Python 3.12** as the minimum supported Python version for all
applications and libraries in this project.

Python 3.12 provides significant improvements that justify it as our
baseline:

* **Improved error messages** — More precise tracebacks and suggestions
  make debugging faster.
* **Performance improvements** — Measurable speedups from comprehension
  inlining and other interpreter optimizations.
* **`type` statement** — First-class syntax for type aliases, improving
  type annotation ergonomics.
* **f-string improvements** — Relaxed restrictions on f-string expressions.
* **Per-interpreter GIL (experimental)** — Foundation for future
  multi-threading improvements.

The `.python-version` file at the repository root specifies the exact
version for local development tooling (e.g., pyenv).

## Considered Options

1. **Python 3.12+ (Chosen):** Modern baseline with strong ecosystem
   support.
    * *Pros:* Excellent error messages, measurable performance gains,
      modern type annotation syntax, active security support.
    * *Cons:* Some older libraries may not yet support 3.12 (rare at this
      point).
2. **Python 3.11:** Previous stable release.
    * *Pros:* Wider library compatibility window.
    * *Cons:* Misses 3.12 performance improvements and language features.
      Will reach end-of-life sooner.
3. **Python 3.13+:** Latest release.
    * *Pros:* Newest features including experimental free-threaded mode.
    * *Cons:* Too new for some production dependencies; ecosystem support
      still maturing.

## Consequences

* **Positive:** Developers benefit from modern Python features, better
  error messages, and performance improvements. Consistent version across
  the project eliminates "works on my machine" issues.
* **Negative:** Contributors must have Python 3.12+ installed locally.
  Some older deployment targets may require updates.
* **Future Implications:** As Python 3.13+ matures, we may raise the
  minimum version via a new ADR that supersedes this one.
