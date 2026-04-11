---
title: "ADR-010: Use Tenacity for Retry Logic"
status: "Accepted"
date: "2026-03-31"
tags:
  - "python"
  - "resilience"
  - "libraries"
---

## Context

* **Problem:** Applications that interact with external services (APIs,
  databases, message queues) need robust retry logic to handle transient
  failures gracefully. Writing custom retry logic is error-prone and leads
  to inconsistent patterns across the codebase.
* **Constraints:** The retry library must support configurable backoff
  strategies, work with both synchronous and asynchronous code, and
  integrate cleanly with Python's exception handling.

## Decision

We will use **[Tenacity](https://tenacity.readthedocs.io/)** as the
standard retry library for all Python applications.

### Key Conventions

* Use Tenacity's decorator syntax for retrying functions.
* Configure **exponential backoff** as the default wait strategy.
* Always set a **stop condition** (max attempts or max time) to prevent
  infinite retries.
* Use `retry_if_exception_type` to retry only on expected transient
  errors.
* Log retry attempts for observability.

### Example

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def fetch_data(url: str) -> dict:
    """Fetch data with automatic retry on transient failures."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
```

## Considered Options

1. **Tenacity (Chosen):** Full-featured retry library for Python.
    * *Pros:* Highly configurable (wait strategies, stop conditions,
      retry conditions), supports sync and async, decorator and
      context manager patterns, active maintenance, well-documented.
    * *Cons:* Additional dependency. Can mask underlying issues if
      retry conditions are too broad.
2. **backoff:** Simpler retry/backoff library.
    * *Pros:* Lightweight, simple API.
    * *Cons:* Fewer features than Tenacity, less flexible configuration,
      smaller community.
3. **Custom retry logic:** Hand-written retry loops.
    * *Pros:* No external dependency.
    * *Cons:* Error-prone, inconsistent across codebase, reinventing
      the wheel, harder to test.
4. **urllib3.util.retry:** Built into urllib3/requests.
    * *Pros:* No extra dependency for HTTP retries.
    * *Cons:* HTTP-only, not usable for database calls, file operations,
      or other retry scenarios.

## Consequences

* **Positive:** Consistent, well-tested retry behavior across all
  applications. Configurable strategies make it easy to tune for
  different failure modes. Reduces boilerplate code.
* **Negative:** Tenacity must be added as a dependency to projects that
  need retry logic. Developers must be careful not to retry on
  non-transient errors.
* **Future Implications:** Retry patterns complement circuit breaker
  patterns for more sophisticated resilience strategies.
