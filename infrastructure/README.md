# Infrastructure

This directory contains [Terraform](https://www.terraform.io/) configuration
for provisioning AWS infrastructure. See
[ADR-016](../meta/adr/ADR-016-terraform_iac.md) for the decision to use
Terraform and [ADR-015](../meta/adr/ADR-015-aws_cloud_provider.md) for the
choice of AWS as cloud provider.

## Directory Structure

```text
infrastructure/
├── main.tf                    # Primary resource definitions
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── providers.tf               # AWS provider configuration
├── versions.tf                # Terraform and provider version constraints
├── backend.tf                 # Remote state backend (S3 + DynamoDB)
├── modules/                   # Reusable Terraform modules
│   └── README.md
├── GITHUB_ACTIONS_ROLE.md     # OIDC role setup guide
├── SETUP.md                   # One-time setup instructions
└── README.md                  # This file
```

## Getting Started

For first-time setup (one-time manual steps), see [SETUP.md](SETUP.md).

For GitHub Actions OIDC role configuration, see
[GITHUB_ACTIONS_ROLE.md](GITHUB_ACTIONS_ROLE.md).

Once setup is complete:

1. **Preview changes:** `terraform plan`
2. **Apply changes:** `terraform apply`
3. **Or let CI handle it:** Open a PR that modifies files in this directory.
   The infrastructure workflow will run `terraform plan` automatically and
   post the results as a PR comment. Changes are applied on merge to `main`.

## Project Configuration

| Setting | Value |
| :--- | :--- |
| AWS Region | `us-west-2` |
| Terraform state bucket | `catch-data-tf-state` |
| Terraform lock table | `catch-data-tf-lock` |
| Project name | `catch-data` |
| Data bucket | `catch-data-{environment}` |
| Silver Lambda | `catch-processing-{environment}` |
| Gold Lambda | `catch-analytics-{environment}` |

## S3 Data Bucket Configuration

The Catch pipeline data bucket is provisioned as `catch-data-{environment}` and
stores Bronze, Silver, and Gold objects in a single bucket using key prefixes.

Key bucket settings:

* Versioning is enabled to preserve prior object versions for rollback.
* Default server-side encryption uses SSE-S3 (`AES256`).
* Bucket-level public access is fully blocked.
* Lifecycle transitions move `bronze/` and `silver/` objects to
  `STANDARD_IA` after 90 days.
* Lifecycle transitions move `bronze/` objects to `DEEP_ARCHIVE` after
  365 days.
* When `var.cors_allowed_origins` is set, a narrow CORS policy allows
  `GET` requests only from that explicit frontend origin list and exposes
  the `ETag` header for cache-aware clients.

Set `cors_allowed_origins` explicitly per environment before applying if the
frontend needs direct browser access to S3-hosted objects.

Bronze schedule uploads trigger the Silver processing Lambda via an S3 event
notification on `s3:ObjectCreated:*` with the `bronze/schedule_` key prefix.
Silver master schedule uploads also trigger the Gold analytics Lambda on
`s3:ObjectCreated:*` with the `silver/master_schedule_` key prefix. This keeps
the Bronze → Silver → Gold pipeline event-driven while avoiding Lambda
invocations for Bronze boxscore and content uploads. Terraform also provisions
an SQS dead-letter queue for the Silver Lambda and exposes its URL to the
function as `SILVER_DLQ_URL` so failed invocation events can be captured for
retry or investigation.

## Lambda Container Configuration

Terraform provisions two reusable `lambda-pipeline-stage` module instances:

* **Silver — `catch-processing-{environment}`**
  * Package type: Lambda container image from the `catch-processing-{environment}`
    ECR repository
  * Memory: `512` MB
  * Timeout: `300` seconds
  * Environment variables: `ENVIRONMENT`, `S3_BUCKET_NAME`, `LOG_FORMAT=json`,
    and `SILVER_DLQ_URL`
  * IAM scope: `s3:GetObject` on `bronze/*`, `s3:PutObject` on `silver/*`, plus
    `sqs:SendMessage` to the Silver DLQ

* **Gold — `catch-analytics-{environment}`**
  * Package type: Lambda container image from the `catch-analytics-{environment}`
    ECR repository
  * Memory: `256` MB
  * Timeout: `120` seconds
  * Environment variables: `ENVIRONMENT`, `S3_BUCKET_NAME`, `LOG_FORMAT=json`
  * IAM scope: `s3:GetObject` on `silver/*` and `s3:PutObject` on `gold/*`

Each ECR repository is immutable, scans images on push, and applies a lifecycle
policy that retains only the last 10 untagged images. Set
`catch_processing_image_tag` and `catch_analytics_image_tag` to a pinned image
tag (for example a git SHA or semantic version) before `terraform apply`.

> **Note:** Never commit real AWS account IDs, ARNs, or credentials to version
> control.
