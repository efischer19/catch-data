---
title: "ADR-008: Use JSON Structured Logging"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "logging"
  - "observability"
---

## Context

* **Problem:** Applications need a consistent logging strategy that
  supports both local development readability and production
  observability. Unstructured log messages are difficult to parse, search,
  and alert on in log aggregation systems.
* **Constraints:** The logging approach must work with Python's standard
  `logging` module, support structured key-value data, and produce output
  that is both human-readable during development and machine-parseable in
  production.

## Decision

We will use **JSON structured logging** as the standard logging format for
all Python applications in production.

### Key Conventions

* Use Python's built-in `logging` module as the foundation.
* Use `python-json-logger` or `structlog` for JSON formatting.
* Log entries must include at minimum: `timestamp`, `level`, `message`,
  and `logger` name.
* Add contextual fields (request ID, user ID, operation name) as
  structured key-value pairs, not embedded in message strings.
* Use **plain text** format for local development (human-readable).
* Use **JSON** format for production and CI environments
  (machine-parseable).
* Configure the format via environment variable
  (e.g., `LOG_FORMAT=json`).

### Example

```python
import logging
logger = logging.getLogger(__name__)

# Good — structured context
logger.info("Order processed", extra={"order_id": "abc-123", "total": 42.50})

# Bad — unstructured string interpolation
logger.info(f"Order abc-123 processed with total 42.50")
```

### Log Levels

| Level | Usage |
| :--- | :--- |
| `DEBUG` | Detailed diagnostic information for development |
| `INFO` | Routine operational events (request handled, job completed) |
| `WARNING` | Unexpected but recoverable situations |
| `ERROR` | Failures that affect a single operation |
| `CRITICAL` | System-wide failures requiring immediate attention |

## Considered Options

1. **JSON structured logging (Chosen):** Machine-parseable logs with
   structured context.
    * *Pros:* Easy to search and filter in log aggregation tools, supports
      structured alerting, standardized format across all services.
    * *Cons:* JSON is harder to read in raw terminal output. Requires a
      formatting library.
2. **Plain text logging:** Human-readable log lines.
    * *Pros:* Easy to read in terminals, no extra dependencies.
    * *Cons:* Difficult to parse programmatically, inconsistent formats
      across services, hard to extract structured data for alerting.
3. **structlog only:** Structured logging library with processors.
    * *Pros:* Powerful processor pipeline, excellent development
      experience.
    * *Cons:* Heavier dependency, steeper learning curve for simple
      use cases.

## Consequences

* **Positive:** Consistent, queryable log output across all services.
  Easier debugging in production with structured context. Compatible
  with any log aggregation platform.
* **Negative:** Slightly more verbose logging setup. JSON output is less
  readable without a log viewer during local development.
* **Future Implications:** Structured logs integrate naturally with
  distributed tracing and metrics collection as observability needs grow.
