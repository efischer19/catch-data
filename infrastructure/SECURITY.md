# Infrastructure Security Review Checklist

This checklist documents the security controls for the catch-data pipeline
infrastructure. Review each item when making IAM or infrastructure changes.
All resources are managed in Terraform — see `main.tf` and
`modules/lambda-pipeline-stage/main.tf`.

## IAM Least Privilege

- [ ] No IAM role or user policy uses `s3:*`, `lambda:*`, `iam:*`, `*`, or
      any other wildcard **action** (e.g., `"Action": "*"`).
- [ ] All IAM policies reference **explicit resource ARNs** — no
      `"Resource": "*"` except where AWS requires it (e.g.,
      `ecr:GetAuthorizationToken`, `sts:GetCallerIdentity`,
      `cloudfront:*` actions that lack resource-level support).
- [ ] Silver Lambda (`catch-processing`) permissions are limited to:
  - `s3:GetObject` on `bronze/*`
  - `s3:PutObject` on `silver/*`
  - `s3:ListBucket` with `s3:prefix` restricted to `bronze/*` and `silver/*`
  - `sqs:SendMessage` to the Silver DLQ only
- [ ] Gold Lambda (`catch-analytics`) permissions are limited to:
  - `s3:GetObject` on `silver/*`
  - `s3:PutObject` on `gold/*`
  - `s3:ListBucket` with `s3:prefix` restricted to `silver/*` and `gold/*`
  - `cloudfront:CreateInvalidation` on the Gold CloudFront distribution ARN only
- [ ] Ingestion IAM user (`catch-data-ingestion-*`) permissions are limited to:
  - `s3:PutObject` on `bronze/*`
  - `s3:ListBucket` with `s3:prefix` restricted to `bronze/*`
  - **No** `s3:GetObject` — no read access to Silver or Gold
- [ ] GitHub Actions OIDC role permissions cover only what CI/CD workflows
      require: ECR push, Lambda update, Terraform state, and specific
      infrastructure management actions scoped to project-named resources.

## S3 Belt-and-Suspenders Bucket Policy

The S3 bucket policy adds a second layer of access control on top of IAM
policies, following the principle of defence in depth.

- [ ] Bucket policy explicitly **denies** Silver Lambda (`catch-processing`)
      `s3:PutObject` and `s3:DeleteObject` on `bronze/*` (Bronze immutability).
- [ ] Bucket policy explicitly **denies** Gold Lambda (`catch-analytics`)
      `s3:PutObject` and `s3:DeleteObject` on `bronze/*` and `silver/*`.
- [ ] Bucket policy explicitly **denies** ingestion IAM user `s3:GetObject`
      on `silver/*` and `gold/*`.
- [ ] CloudFront OAC is the **only** principal granted `s3:GetObject` on
      `gold/*` via the bucket policy.
- [ ] All four S3 public access block settings are `true` on the data bucket.

## Encryption

- [ ] S3 data bucket has AES-256 server-side encryption enabled by default.
- [ ] Terraform remote state bucket (`catch-data-tf-state`) uses
      `encrypt = true` in `backend.tf`.
- [ ] CloudFront distribution enforces HTTPS
      (`viewer_protocol_policy = "redirect-to-https"`).

## GitHub OIDC Trust Policy

- [ ] Trust policy includes `StringEquals` on the `aud` claim:
      `token.actions.githubusercontent.com:aud = sts.amazonaws.com`.
- [ ] Trust policy includes `StringLike` on the `sub` claim, scoped to this
      repository only:
      `token.actions.githubusercontent.com:sub = repo:efischer19/catch-data:*`.
- [ ] No long-lived AWS credentials are stored in GitHub Secrets (no
      `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).
- [ ] GitHub Actions role ARN is referenced as
      `arn:aws:iam::<AWS_ACCOUNT_ID>:role/catch-data-github-actions`
      in workflow files, not hardcoded.

## Ingestion Credentials (Mac Mini)

- [ ] IAM user access keys are rotated at least every 90 days.
- [ ] Access keys are stored in `~/.aws/credentials` on the Mac Mini;
      they are **never** committed to the repository.
- [ ] Consider migrating to **AWS IAM Identity Center** for automatic
      credential rotation and MFA enforcement.

## ECR Image Security

- [ ] All ECR repositories have `image_tag_mutability = "IMMUTABLE"` to
      prevent tag overwrites and ensure reproducible Lambda deployments.
- [ ] ECR image scanning on push (`scan_on_push = true`) is enabled for all
      repositories to detect OS and library CVEs.

## Audit and Observability

- [ ] AWS CloudTrail is enabled in the account for management events (free
      tier; covers IAM role assumptions, S3 bucket policy changes, etc.).
- [ ] Consider enabling S3 **data event** logging for the `catch-data-*`
      bucket to audit all object reads and writes
      (cost: ~$0.10 per 100,000 events — negligible at ~100 events/night).
- [ ] Review AWS IAM Access Analyzer findings regularly to detect unintended
      cross-account or public resource exposure.

## Terraform and CI/CD Security

- [ ] Run `tfsec` or `checkov` in CI (or as a pre-commit hook) to scan for
      overly permissive IAM policies and other misconfigurations.
- [ ] Provider versions are pinned in `versions.tf` for reproducible builds.
- [ ] Terraform state is stored with encryption (`encrypt = true`) and
      DynamoDB locking to prevent concurrent state corruption.
- [ ] `terraform validate` and `terraform fmt -check` pass on every PR
      (enforced by the infrastructure workflow).
- [ ] All Terraform resources include `Project`, `Environment`, and
      `ManagedBy` tags for cost attribution and operational visibility.

## References

- [ADR-015: AWS as Cloud Provider](../meta/adr/ADR-015-aws_cloud_provider.md)
- [ADR-016: Terraform for IaC](../meta/adr/ADR-016-terraform_iac.md)
- [ADR-017: GitHub OIDC for AWS Authentication](../meta/adr/ADR-017-github_oidc_aws_auth.md)
- [ADR-018: Medallion Architecture](../meta/adr/ADR-018-medallion_architecture.md)
- [GITHUB_ACTIONS_ROLE.md](GITHUB_ACTIONS_ROLE.md) — OIDC provider bootstrap guide
