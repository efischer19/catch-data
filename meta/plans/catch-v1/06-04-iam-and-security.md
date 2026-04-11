Title: feat: Terraform IAM roles and security policies for pipeline

## What do you want to build?

Define the complete IAM security model for the Catch data pipeline. This
includes execution roles for each Lambda, a role for the Mac Mini ingestion
script, and the GitHub Actions OIDC role for CI/CD deployments. All roles
follow the principle of least privilege.

## Acceptance Criteria

- [ ] Silver Lambda execution role: `s3:GetObject` on `bronze/*`, `s3:PutObject` on `silver/*`, `s3:ListBucket` with prefix restrictions
- [ ] Gold Lambda execution role: `s3:GetObject` on `silver/*`, `s3:PutObject` on `gold/*`, `s3:ListBucket` with prefix restrictions
- [ ] Gold Lambda role includes `cloudfront:CreateInvalidation` permission for the Gold CloudFront distribution
- [ ] Ingestion IAM user/role: `s3:PutObject` on `bronze/*` only — no read access to Silver or Gold
- [ ] GitHub Actions OIDC role (per ADR-017): permissions to push ECR images and update Lambda functions
- [ ] No IAM role has `s3:*` or `*` wildcard permissions
- [ ] All IAM policies are defined in Terraform with explicit resource ARNs
- [ ] IAM roles include condition keys where possible (e.g., OIDC subject claims for GitHub Actions)
- [ ] A security review checklist is documented in `infrastructure/SECURITY.md` or similar
- [ ] All Terraform changes pass `terraform validate` and `terraform plan`

## Implementation Notes

**🔧 Data Pipeline Janitor notes:**

- Least-privilege IAM is the most important security control. Each pipeline
  stage should only access the S3 prefixes it needs.
- The Silver Lambda must NOT have write access to Bronze (immutability
  guarantee). The Gold Lambda must NOT have write access to Silver.
- Consider adding S3 bucket policies that enforce prefix-based access as a
  second layer of defense (belt-and-suspenders with IAM policies).

**🤑 FinOps Miser notes:**

- IAM is free. There is no cost concern here — invest heavily in security.
- Consider enabling AWS CloudTrail for the S3 bucket to audit all access.
  CloudTrail's free tier includes management events. Data events (S3 object
  access) cost $0.10 per 100,000 events. At ~100 events/night, this is
  effectively free.

**😴 Lazy Maintainer notes:**

- The ingestion role for the Mac Mini should use long-lived credentials stored
  securely (e.g., `~/.aws/credentials`). Alternatively, consider AWS SSO or
  IAM Identity Center for credential rotation.
- GitHub Actions OIDC (ADR-017) eliminates the need for long-lived CI/CD
  credentials. The OIDC role's trust policy should restrict to the
  `catch-data` repository and specific branches/environments.

**🧪 QA notes:**

- Write a Terraform plan test (or use `tfsec`/`checkov`) to scan for
  overly permissive IAM policies. This can be a CI check.

Reference ADR-015 (AWS), ADR-016 (Terraform), ADR-017 (GitHub OIDC).
