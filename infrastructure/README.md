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

S3 event notifications are intentionally not configured yet; they will be added
once the downstream Lambda functions exist.

> **Note:** Never commit real AWS account IDs, ARNs, or credentials to version
> control.
