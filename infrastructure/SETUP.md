# Infrastructure Setup Guide

This guide covers the **one-time manual setup steps** required before the
GitHub Actions workflows can manage your AWS infrastructure automatically.
See [ADR-016](../meta/adr/ADR-016-terraform_iac.md) and
[ADR-017](../meta/adr/ADR-017-github_oidc_aws_auth.md) for background.

## Prerequisites

- AWS account with administrative access
- [Terraform](https://developer.hashicorp.com/terraform/install) installed
  locally
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
  installed (optional, for verification)
- Access to this GitHub repository's settings

## Step 1 — Create the Terraform State Backend

Terraform needs an S3 bucket and DynamoDB table for remote state storage
and locking. Create these **before** running `terraform init`:

### Using the AWS Console

1. **S3 Bucket:**
   - Go to S3 → Create bucket
   - Bucket name: `{{TF_STATE_BUCKET}}` (e.g., `my-project-tf-state`)
   - Region: `{{AWS_REGION}}`
   - Enable versioning
   - Enable server-side encryption (SSE-S3)
   - Block all public access

2. **DynamoDB Table:**
   - Go to DynamoDB → Create table
   - Table name: `{{TF_LOCK_TABLE}}` (e.g., `my-project-tf-lock`)
   - Partition key: `LockID` (String)
   - Use on-demand capacity mode

### Using the AWS CLI

```bash
# Create S3 bucket for state (replace placeholders)
# Note: For us-east-1, omit --create-bucket-configuration.
# For all other regions, include it with the correct LocationConstraint.
aws s3api create-bucket \
  --bucket {{TF_STATE_BUCKET}} \
  --region {{AWS_REGION}} \
  --create-bucket-configuration LocationConstraint={{AWS_REGION}}

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket {{TF_STATE_BUCKET}} \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket {{TF_STATE_BUCKET}} \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Block public access
aws s3api put-public-access-block \
  --bucket {{TF_STATE_BUCKET}} \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name {{TF_LOCK_TABLE}} \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region {{AWS_REGION}}
```

## Step 2 — Configure GitHub Actions Authentication

Follow the [GITHUB_ACTIONS_ROLE.md](GITHUB_ACTIONS_ROLE.md) guide to set
up OIDC authentication between GitHub Actions and AWS.

## Step 3 — Replace Placeholder Values

Search for `{{...}}` placeholders across the repository and replace them
with your real values:

| Placeholder | Description | Example |
| :--- | :--- | :--- |
| `{{AWS_ACCOUNT_ID}}` | Your AWS account ID | `123456789012` |
| `{{AWS_REGION}}` | Target AWS region | `us-east-1` |
| `{{TF_STATE_BUCKET}}` | S3 bucket for Terraform state | `my-project-tf-state` |
| `{{TF_LOCK_TABLE}}` | DynamoDB table for state locking | `my-project-tf-lock` |
| `{{PROJECT_NAME}}` | Your project name | `my-data-project` |
| `{{GITHUB_OWNER}}` | GitHub org or user | `my-org` |

## Step 4 — Set GitHub Repository Secrets and Variables

Add the following in your repository's **Settings → Secrets and variables
→ Actions**:

### Secrets

| Name | Value |
| :--- | :--- |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID |

### Variables

| Name | Value |
| :--- | :--- |
| `AWS_REGION` | Target AWS region (e.g., `us-east-1`) |

## Step 5 — Initialize and Apply

```bash
cd infrastructure

# Initialize Terraform (connects to remote state backend)
terraform init

# Preview changes
terraform plan

# Apply changes (creates AWS resources)
terraform apply
```

## Verification

After completing setup:

1. **Verify state backend:** `terraform state list` should work without
   errors
2. **Verify GitHub Actions:** Open a PR that modifies a file in
   `infrastructure/` — the workflow should post a Terraform plan comment
3. **Verify resources:** `terraform output` should show your S3 bucket,
   ECR repository, and Lambda function details

## Troubleshooting

### "Error assuming role"

- Verify the `AWS_ACCOUNT_ID` secret is correct in GitHub
- Check that the OIDC provider exists in IAM
- Ensure the role trust policy references your repository correctly

### "Error initializing backend"

- Verify the S3 bucket and DynamoDB table exist
- Check that the bucket name and table name in `backend.tf` match what
  you created
- Ensure your AWS credentials have access to the state backend

### "Access denied" during plan/apply

- Verify the IAM role has the required permissions
- Check AWS CloudTrail for detailed error information

## Security Notes

- ✅ Never commit real AWS account IDs or credentials to version control
- ✅ Use GitHub Secrets for sensitive values
- ✅ Enable S3 versioning on the state bucket for recovery
- ✅ DynamoDB locking prevents concurrent state modifications

## Next Steps

Once setup is complete:

- The infrastructure workflow automatically runs `terraform plan` on PRs
- Approved changes are applied when merged to `main`
- Manual runs are available via the Actions tab
- Add new resources by editing `infrastructure/main.tf`
