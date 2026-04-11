# feat: Configure Silver-to-Gold trigger and Gold output validation

## What do you want to build?

Set up the S3 event notification that triggers the Gold generation Lambda when
the Silver layer is updated, and add output validation to ensure all Gold files
are well-formed before they reach CloudFront and the frontend.

## Acceptance Criteria

- [ ] An S3 event notification triggers the Gold Lambda on `s3:ObjectCreated:*` events with key prefix `silver/master_schedule_`
- [ ] The event notification is defined in Terraform
- [ ] The Lambda has IAM permissions to read from `silver/` and write to `gold/`
- [ ] After writing all Gold files, the Lambda reads each one back and validates it against the Gold Pydantic models (write-then-verify)
- [ ] If any Gold file fails validation, the Lambda logs an error with the file key and validation details
- [ ] Invalid Gold files are NOT overwritten — the previous valid version remains (S3 versioning preserves it)
- [ ] A summary log entry records: files written, files validated, files failed
- [ ] CloudFront cache invalidation is triggered after successful Gold writes (if CloudFront is configured)
- [ ] Unit tests verify: trigger configuration, validation logic, behavior on validation failure
- [ ] All tests pass via `poetry run pytest` in `apps/catch-analytics`

## Implementation Notes

**🔧 Data Pipeline Janitor notes:**

- The write-then-verify pattern catches bugs where `model_dump()` produces
  output that doesn't round-trip through `model_validate()`. This can happen
  with edge-case data types (dates, enums, optional fields).
- If validation fails after write, the "bad" file is already in S3. However,
  S3 versioning means the previous valid version is still accessible. A
  follow-up step could explicitly restore the previous version, but for V1,
  logging the error is sufficient — the nightly pipeline will overwrite it
  the next night.

**😴 Lazy Maintainer notes:**

- The entire Bronze → Silver → Gold pipeline runs automatically each night
  via S3 event chaining. No orchestrator (Step Functions, Airflow) is needed.
  This is the simplest possible architecture.
- If the Gold Lambda fails, the previous Gold files remain in S3 and
  CloudFront continues to serve them. The frontend is unaffected by a single
  night's failure.

**🤑 FinOps Miser notes:**

- CloudFront cache invalidation: the first 1,000 invalidation paths per month
  are free. We invalidate ~31 paths per night (30 team files + 1 upcoming) ×
  30 nights/month = ~930 paths/month. Safely within the free tier.
- If CloudFront is not yet configured (see ticket 06-03), skip the
  invalidation step and add it when CloudFront is deployed.

**⚡ PWA Performance Fanatic notes:**

- CloudFront cache invalidation ensures the frontend always gets fresh Gold
  data after the nightly pipeline runs. Without invalidation, cached stale
  data could persist for hours (depending on TTL settings).

Terraform resources needed:

- `aws_s3_bucket_notification` for Silver → Gold trigger (extend the existing
  notification configuration from ticket 04-02)
- `aws_lambda_permission` for S3 → Lambda invocation

Reference ADR-018 (Medallion Architecture) for the Gold layer conventions.
