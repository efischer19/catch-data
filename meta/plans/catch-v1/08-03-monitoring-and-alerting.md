Title: feat: Pipeline monitoring, alerting, and operational runbook

## What do you want to build?

Implement lightweight monitoring and alerting for the nightly data pipeline so
that failures are detected and surfaced automatically. The goal is zero daily
manual checks — the system should be silent when healthy and loud when broken.

## Acceptance Criteria

- [ ] CloudWatch Log Groups are defined in Terraform for both Lambda functions with 14-day retention
- [ ] Structured JSON log entries from Lambdas include: `pipeline_stage`, `execution_date`, `games_processed`, `games_failed`, `duration_ms`
- [ ] A CloudWatch Alarm fires when either Lambda's error count exceeds 0 in a 24-hour period
- [ ] A CloudWatch Alarm fires when the Gold layer files are older than 36 hours (stale data detection)
- [ ] Alarm notifications are sent to an SNS topic (email subscriber configurable via Terraform variable)
- [ ] An operational runbook is documented in `docs-src/` or `meta/`: common failure modes, how to manually re-trigger pipeline stages, how to roll back a bad Gold file
- [ ] The ingestion script (Mac Mini) logs to a local file with structured JSON and includes a health-check output
- [ ] All Terraform resources pass `terraform validate` and `terraform plan`

## Implementation Notes

**😴 Lazy Maintainer notes:**

- The 36-hour staleness alarm is the most important alert. If Gold files
  haven't been updated in 36 hours, something in the pipeline is broken —
  either ingestion didn't run, or a Lambda failed. The 36-hour window allows
  for late West Coast games and pipeline execution time.
- The runbook should cover:
  1. How to check ingestion logs on the Mac Mini
  2. How to re-run the ingestion script for a specific date
  3. How to manually trigger the Silver Lambda
  4. How to manually trigger the Gold Lambda
  5. How to restore a previous Gold file version from S3 versioning

**🤑 FinOps Miser notes:**

- CloudWatch Logs: 14-day retention minimizes storage cost. At a few KB of
  logs per night, this is effectively free.
- CloudWatch Alarms: first 10 alarms are free. We need 2-4 alarms. No cost.
- SNS email notifications: free tier includes 1,000 emails/month. We'll send
  at most a few per month. No cost.
- **Do not** use CloudWatch Dashboards for V1 — they cost $3/month per
  dashboard. The alarms and logs are sufficient for monitoring.

**🔧 Data Pipeline Janitor notes:**

- The stale-data alarm should check the `LastModified` timestamp of
  `gold/upcoming_games.json` in S3. This is a single `s3:HeadObject` call
  that can run in a lightweight Lambda on a CloudWatch Events schedule
  (hourly during MLB season).
- Alternatively, use S3 Inventory or CloudWatch Metrics if available. But a
  simple scheduled Lambda is the most transparent approach.

**🧪 QA notes:**

- The monitoring infrastructure itself should be tested by manually triggering
  a failure (e.g., deleting a Bronze file) and verifying the alarm fires.
  Document this as a manual acceptance test in the runbook.

Terraform resources:

- `aws_cloudwatch_log_group` × 2
- `aws_cloudwatch_metric_alarm` (Lambda errors, stale data)
- `aws_sns_topic` + `aws_sns_topic_subscription` (email)

Reference ADR-008 (JSON logging), ADR-015 (AWS), ADR-016 (Terraform).
