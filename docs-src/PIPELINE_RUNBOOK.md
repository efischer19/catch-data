# Pipeline Operations Runbook

This runbook covers the nightly catch-data pipeline — from Mac Mini ingestion
through Silver processing to Gold output.  Consult it when a monitoring alert
fires or when manual intervention is needed.

## Architecture Overview

```text
Mac Mini (cron)          AWS Lambda               S3 (medallion)
─────────────           ────────────             ───────────────
catch-ingestion   →  bronze/  →  catch-processing  →  silver/
                                  catch-analytics  →  gold/
```

Alarms and notifications are delivered via SNS (email).  See
`infrastructure/main.tf` for the full alarm definitions.

---

## Monitoring Alerts

### Alert: `catch-data-catch-processing-errors-{env}`

**Meaning**: The Silver Lambda (catch-processing) threw at least one unhandled
exception in the last 24 hours.

**Likely causes**:

- Malformed Bronze file (schema change in the MLB Stats API)
- S3 permission error (check IAM role for `catch-processing-{env}`)
- Cold-start timeout (Lambda memory or timeout too low)

**Actions**: See [How to re-run the Silver Lambda](#how-to-re-run-the-silver-lambda).

---

### Alert: `catch-data-catch-analytics-errors-{env}`

**Meaning**: The Gold Lambda (catch-analytics) threw at least one unhandled
exception in the last 24 hours.

**Likely causes**:

- Missing or corrupt Silver master schedule
- CloudFront invalidation failure
- Gold validation failure (broken Pydantic model round-trip)

**Actions**: See [How to re-run the Gold Lambda](#how-to-re-run-the-gold-lambda).

---

### Alert: `catch-data-gold-data-stale-{env}`

**Meaning**: catch-analytics has **not been invoked** in the last 36 hours.
This means Gold files have not been refreshed — either ingestion did not run
on the Mac Mini, or an upstream Lambda failed silently.

The 36-hour window accounts for late West Coast games and pipeline execution
time.

**Actions**:

1. [Check ingestion logs on the Mac Mini](#how-to-check-ingestion-logs-on-the-mac-mini)
2. If ingestion ran but Silver/Gold Lambdas did not trigger, check the S3
   notification configuration in the AWS console.
3. [Re-run ingestion manually](#re-run-ingestion-for-a-specific-date), then
   verify downstream Lambdas are triggered.

---

## How to Check Ingestion Logs on the Mac Mini

The ingestion script writes structured JSON to the file path configured in
the `LOG_FILE` environment variable (e.g., `~/.catch-data/ingestion.log`).
Cron output is also captured to `/tmp/catch-ingestion-cron.log` by
convention.

```bash
# Tail the structured log file
tail -n 50 ~/.catch-data/ingestion.log | python3 -m json.tool

# Check cron output
cat /tmp/catch-ingestion-cron.log

# View the health-check summary for the last run
tail -n 1 /tmp/catch-ingestion-cron.log | python3 -c "import sys,json; d=json.load(sys.stdin); print('exit=', d.get('games_failed'), 'failed,', d.get('games_succeeded'), 'ok')"
```

Each run emits a final JSON object to stdout.  The key fields:

| Field | Meaning |
| :--- | :--- |
| `pipeline_stage` | Always `"bronze"` for ingestion |
| `execution_date` | Date that was ingested (`YYYY-MM-DD`) |
| `games_processed` | Games that required a fetch/upload |
| `games_failed` | Games where the API call or upload failed |
| `duration_ms` | Total wall-clock duration in milliseconds |
| `games_succeeded` | Games written successfully |

---

## Re-run Ingestion for a Specific Date

Log into the Mac Mini and run:

```bash
cd /path/to/catch-data
export S3_BUCKET_NAME=catch-data-prod   # or catch-data-dev
export LOG_FORMAT=json
export LOG_FILE=~/.catch-data/ingestion.log

poetry run python -m app.main ingest-games --date 2026-07-04 --bucket "$S3_BUCKET_NAME"
```

Exit codes:

- `0` — all games succeeded
- `1` — partial failure (some games failed, check `failed_games.json`)
- `2` — complete failure (no games succeeded, or schedule unavailable)

!!! warning
    Re-ingesting a date that already has Bronze files will **skip** existing
    objects (idempotent by default).  This is safe to run multiple times.

---

## How to Re-run the Silver Lambda

### Via AWS CLI

```bash
# Invoke the Silver Lambda for season year 2026
aws lambda invoke \
  --function-name catch-processing-prod \
  --payload '{"Records":[{"s3":{"bucket":{"name":"catch-data-prod"},"object":{"key":"bronze/schedule_2026.json"}}}]}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/silver-response.json

cat /tmp/silver-response.json
```

### Via AWS Console

1. Open **Lambda → catch-processing-{env} → Test**.
2. Use the following test event payload:

   ```json
   {
     "Records": [
       {
         "s3": {
           "bucket": { "name": "catch-data-prod" },
           "object": { "key": "bronze/schedule_2026.json" }
         }
       }
     ]
   }
   ```

3. Click **Test** and review the response for `games_written` and
   `processing_errors_count`.

---

## How to Re-run the Gold Lambda

### Via AWS CLI

```bash
# Invoke the Gold Lambda for season year 2026
aws lambda invoke \
  --function-name catch-analytics-prod \
  --payload '{"Records":[{"s3":{"bucket":{"name":"catch-data-prod"},"object":{"key":"silver/master_schedule_2026.json"}}}]}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/gold-response.json

cat /tmp/gold-response.json
```

### Via AWS Console

1. Open **Lambda → catch-analytics-{env} → Test**.
2. Use the following test event payload:

   ```json
   {
     "Records": [
       {
         "s3": {
           "bucket": { "name": "catch-data-prod" },
           "object": { "key": "silver/master_schedule_2026.json" }
         }
       }
     ]
   }
   ```

3. Click **Test** and review `files_written`, `files_validated`, and
   `files_failed`.

---

## How to Roll Back a Bad Gold File

Because S3 versioning is enabled on the data bucket, you can restore a
previous version of any Gold object.

### Via AWS CLI

```bash
# List available versions of upcoming_games.json
aws s3api list-object-versions \
  --bucket catch-data-prod \
  --prefix gold/upcoming_games.json \
  --query 'Versions[*].[VersionId,LastModified]' \
  --output table

# Restore a specific version by copying it over the current object
aws s3api copy-object \
  --bucket catch-data-prod \
  --copy-source "catch-data-prod/gold/upcoming_games.json?versionId=<VERSION_ID>" \
  --key gold/upcoming_games.json
```

Replace `<VERSION_ID>` with the version ID from the list above.

### Via AWS Console

1. Open **S3 → catch-data-prod → gold/upcoming_games.json**.
2. Click the **Versions** tab.
3. Select the version you want to restore and click **Download** to verify
   it looks correct.
4. Click **Copy** and copy it back to the same key to make it current, **or**
   use the CLI copy-object command above.

After restoring, invalidate the CloudFront cache so the CDN serves the
restored file immediately:

```bash
aws cloudfront create-invalidation \
  --distribution-id <CLOUDFRONT_DISTRIBUTION_ID> \
  --paths "/gold/upcoming_games.json" "/gold/team_*.json"
```

The `CLOUDFRONT_DISTRIBUTION_ID` is available in the Terraform outputs:

```bash
cd infrastructure
terraform output cloudfront_distribution_id
```

---

## Manual Acceptance Test for Monitoring Infrastructure

To verify alarms fire correctly, follow these steps in a development
environment only:

1. **Trigger a Lambda error alarm**: In the dev environment, invoke
   `catch-processing-dev` with an invalid event payload.  After Lambda
   records the error, wait up to 1 evaluation period (24 h) or lower the
   alarm threshold temporarily via the AWS console.  Verify an SNS email
   arrives at the configured `alert_email` address.

2. **Trigger the stale data alarm**: Suspend the nightly cron job on the
   Mac Mini for 36+ hours (or set the `gold_data_stale` alarm period to a
   shorter value for testing).  Verify the SNS email arrives.

3. **Verify logs contain required fields**: After a normal ingestion run,
   inspect CloudWatch Logs for `/aws/lambda/catch-processing-{env}`.  The
   `lambda_execution_summary` log entry must include `pipeline_stage`,
   `execution_date`, `games_processed`, `games_failed`, and `duration_ms`.

---

## Useful Commands

```bash
# View recent CloudWatch logs for Silver Lambda
aws logs tail /aws/lambda/catch-processing-prod --since 24h --format short

# View recent CloudWatch logs for Gold Lambda
aws logs tail /aws/lambda/catch-analytics-prod --since 24h --format short

# Check current alarm states
aws cloudwatch describe-alarms \
  --alarm-name-prefix catch-data \
  --query 'MetricAlarms[*].[AlarmName,StateValue,StateReason]' \
  --output table

# List SNS subscriptions for the pipeline alerts topic
aws sns list-subscriptions-by-topic \
  --topic-arn $(cd infrastructure && terraform output -raw sns_pipeline_alerts_topic_arn)
```
