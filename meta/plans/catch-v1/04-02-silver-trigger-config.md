Title: feat: Configure S3 event notification for Bronze-to-Silver trigger

## What do you want to build?

Set up the S3 event notification that triggers the Silver processing Lambda
whenever a new Bronze schedule file is uploaded. This creates the automated
Bronze → Silver data flow so that nightly ingestion automatically produces
updated Silver data without manual intervention.

## Acceptance Criteria

- [ ] An S3 event notification is configured on the data bucket for `s3:ObjectCreated:*` events with key prefix `bronze/schedule_`
- [ ] The notification triggers the Silver processing Lambda function
- [ ] The event notification is defined in Terraform (not configured manually in AWS Console)
- [ ] The Lambda function has the necessary IAM permissions to be invoked by S3
- [ ] The Lambda's resource policy allows `s3.amazonaws.com` to invoke it
- [ ] A test upload of a `bronze/schedule_*.json` file triggers the Lambda (verified via CloudWatch logs)
- [ ] Uploading non-schedule Bronze files (boxscore, content) does NOT trigger the Silver Lambda
- [ ] The Terraform configuration is added to `infrastructure/main.tf` (or a new module)

## Implementation Notes

**🔧 Data Pipeline Janitor notes:**

- The trigger fires on `bronze/schedule_` prefix only, not on every Bronze
  upload. This is intentional: the schedule upload is the last step in the
  nightly ingestion (it runs after boxscores and content are already
  uploaded). This ensures the Silver Lambda can find all the game data it
  needs.
- **Ordering concern:** If the ingestion script uploads boxscores, then
  content, then the schedule — the schedule upload triggers the Silver
  Lambda, which reads the boxscores and content that are already in S3.
  Document this ordering dependency in the ingestion script.
- If the schedule is re-uploaded (e.g., a manual re-run), the Silver Lambda
  fires again. This is safe because Silver processing is idempotent (full
  rebuild).

**😴 Lazy Maintainer notes:**

- S3 event notifications are fire-and-forget — no polling, no cron, no
  orchestrator needed. AWS handles the trigger automatically.
- If the Lambda fails, the event is not retried by default. Consider adding
  a dead-letter queue (SQS) for failed invocations. This can be a follow-up
  if needed.

**🤑 FinOps Miser notes:**

- S3 event notifications are free. The Lambda invocation cost is the only
  charge, and it's ~$0.0000002 per invocation at 512 MB / 60 seconds.

Terraform resource types needed:

- `aws_s3_bucket_notification` for the event configuration
- `aws_lambda_permission` to allow S3 to invoke the Lambda

Reference ADR-016 (Terraform) and ADR-018 (Medallion Architecture).
