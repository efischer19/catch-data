Title: feat: Add Silver layer error handling and data quality checks

## What do you want to build?

Add robust error handling, data quality validation, and dead-letter strategies
to the Silver processing Lambda. The Silver layer is the single source of truth
(SSOT) — its output quality directly determines the quality of the Gold layer
and the user experience. Errors here must be caught, logged, and surfaced.

## Acceptance Criteria

- [ ] Individual game processing failures are caught and logged without aborting the entire Lambda run
- [ ] A `processing_errors` summary is included in the Silver output metadata: count of games that failed processing, with gamePk list
- [ ] Data quality checks run after Silver assembly: total game count matches expected (±5% of Bronze schedule count), no duplicate gamePk values
- [ ] If more than 20% of games fail processing, the Lambda exits with an error (do not write a severely degraded Silver file)
- [ ] Pydantic `ValidationError` on individual games is caught, logged with the offending data, and the game is excluded
- [ ] A CloudWatch metric or structured log field enables alerting on processing failures
- [ ] If the Lambda fails entirely (uncaught exception), an SQS dead-letter queue receives the failed event for later retry or investigation
- [ ] Unit tests verify: partial failure handling, quality gate threshold, DLQ routing
- [ ] All tests pass via `poetry run pytest` in `apps/catch-processing`

## Implementation Notes

**🔧 Data Pipeline Janitor notes:**

- The 20% failure threshold is a safety valve. If the MLB API changed its
  response format, many games would fail Pydantic validation. Writing a Silver
  file with 80% of games missing would cause downstream damage. Better to fail
  loudly and keep the previous Silver file intact.
- The quality check should compare the number of `SilverGame` objects to the
  number of games in the Bronze schedule. A small difference is expected
  (Spring Training filtering, postponed games) but a large gap signals a
  problem.
- Log each excluded game at WARNING level with: `gamePk`, error type, and a
  truncated sample of the offending data (not the full payload, to avoid
  log bloat).

**😴 Lazy Maintainer notes:**

- The dead-letter queue (SQS) is a safety net. In practice, the Lambda should
  rarely fail entirely. If it does, the DLQ message can be manually redriven
  or used to trigger an alert.
- Consider adding a CloudWatch alarm that fires when the DLQ has > 0 messages.
  This is a follow-up ticket if a notification channel is decided.

**🤑 FinOps Miser notes:**

- SQS dead-letter queue: the first 1 million SQS requests per month are free.
  This DLQ will receive at most a few messages per month (if any). Zero cost.
- CloudWatch log storage: structured JSON logs with verbose error details could
  add up if there are many failures. Set a 14-day log retention policy to
  contain costs.

**🧪 QA notes:**

- Write a parameterized test that injects N failing games out of M total and
  verifies: at N/M < 20%, Silver file is written with M-N games; at N/M ≥
  20%, Lambda raises an error and writes nothing.
- Test the DLQ integration by mocking the SQS client and verifying the
  message payload.

Reference ADR-018 (Medallion Architecture) for data-quality-between-layers
guidance.
