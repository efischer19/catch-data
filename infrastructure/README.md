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

## Placeholder Values

| Placeholder | Description | Example |
| :--- | :--- | :--- |
| `{{AWS_ACCOUNT_ID}}` | Your AWS account ID | `123456789012` |
| `{{AWS_REGION}}` | Target AWS region | `us-east-1` |
| `{{TF_STATE_BUCKET}}` | S3 bucket for Terraform state | `my-project-tf-state` |
| `{{TF_LOCK_TABLE}}` | DynamoDB table for state locking | `my-project-tf-lock` |
| `{{PROJECT_NAME}}` | Your project name | `my-data-project` |

> **Note:** Never commit real AWS account IDs, ARNs, or credentials to version
> control.
