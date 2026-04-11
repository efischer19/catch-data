# GitHub Actions IAM Role Configuration

This guide explains how to set up the IAM role that allows GitHub Actions
workflows to authenticate to AWS using OIDC federation. See
[ADR-017](../meta/adr/ADR-017-github_oidc_aws_auth.md) for the decision
to use OIDC instead of long-lived access keys.

## Overview

GitHub Actions workflows authenticate to AWS using short-lived OIDC tokens.
This requires:

1. An **IAM OIDC identity provider** that trusts GitHub's token issuer
2. An **IAM role** with a trust policy scoped to your repository

No long-lived AWS credentials are stored in GitHub Secrets.

## Prerequisites

- AWS account with IAM administrative access
- This GitHub repository (to scope the trust policy)

## Step 1 — Create the OIDC Identity Provider

If your AWS account does not already have a GitHub OIDC provider:

### Using the AWS Console

1. Go to **IAM → Identity providers → Add provider**
2. Provider type: **OpenID Connect**
3. Provider URL: `https://token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`
5. Click **Add provider**

### Using the AWS CLI

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
                    1c58a3a8518e8759bf075b76b750d4f2df264fcd
```

> **Note:** You only need one OIDC provider per AWS account, even if
> multiple repositories use it.

## Step 2 — Create the IAM Role

### Trust Policy

Create a role with a trust policy that allows your repository to assume it.
Replace `{{AWS_ACCOUNT_ID}}`, `{{GITHUB_OWNER}}`, and `{{PROJECT_NAME}}`
with your real values:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::{{AWS_ACCOUNT_ID}}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:{{GITHUB_OWNER}}/{{PROJECT_NAME}}:*"
        }
      }
    }
  ]
}
```

### Using the AWS Console

1. Go to **IAM → Roles → Create role**
2. Trusted entity type: **Web identity**
3. Identity provider: `token.actions.githubusercontent.com`
4. Audience: `sts.amazonaws.com`
5. Role name: `{{PROJECT_NAME}}-github-actions`
6. Attach an inline policy with the permissions below

### Using the AWS CLI

Save the trust policy above to `trust-policy.json`, then:

```bash
aws iam create-role \
  --role-name {{PROJECT_NAME}}-github-actions \
  --assume-role-policy-document file://trust-policy.json
```

## Step 3 — Attach Permissions

The role needs permissions to manage your infrastructure via Terraform.
Attach an inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "ecr:*",
        "lambda:*",
        "iam:*",
        "logs:*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note:** This is a broad bootstrap policy suitable for initial setup.
> Once your infrastructure is running, replace it with least-privilege
> permissions scoped to the specific resources and actions your project
> needs (e.g., restrict `s3:*` to `s3:GetObject`, `s3:PutObject` on
> specific bucket ARNs).

## Step 4 — Configure GitHub Repository

Add the following as GitHub Actions **secrets** or **variables**:

| Name | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `AWS_ACCOUNT_ID` | Secret | Your AWS account ID | `123456789012` |
| `AWS_ROLE_ARN` | Secret | ARN of the role created above | `arn:aws:iam::123456789012:role/my-project-github-actions` |
| `AWS_REGION` | Variable | Target AWS region | `us-east-1` |

## Verification

After setup, test by triggering the infrastructure workflow:

1. Make a small change to any file in `infrastructure/`
2. Open a pull request
3. The workflow should successfully assume the role and run
   `terraform plan`

If authentication fails, check:

- The OIDC provider exists in your AWS account
- The role trust policy references the correct repository
- The `AWS_ACCOUNT_ID` secret is set correctly in GitHub

## Security Benefits

- **No long-lived credentials** — OIDC tokens are short-lived and
  automatically rotated
- **Repository-scoped access** — the trust policy restricts which
  repositories can assume the role
- **Audit trail** — AWS CloudTrail logs every role assumption
- **Least privilege** — permissions can be scoped per role and per
  workflow

## References

- [GitHub Docs: Configuring OIDC in AWS](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
- [AWS Docs: Creating OIDC Identity Providers](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [ADR-017: GitHub OIDC for AWS Authentication](../meta/adr/ADR-017-github_oidc_aws_auth.md)
