# feat: Terraform S3 bucket configuration with event notifications

## What do you want to build?

Update the Terraform infrastructure to configure the S3 data bucket specifically
for the Catch pipeline. This includes bucket lifecycle policies, CORS
configuration for frontend access, and the foundational bucket settings. S3
event notifications will be added by tickets 04-02 and 05-03 once the Lambda
functions are defined.

## Acceptance Criteria

- [ ] The S3 bucket is named `catch-data-{environment}` (e.g., `catch-data-prod`)
- [ ] Versioning is enabled on the bucket (preserves historical data, enables rollback)
- [ ] Server-side encryption (AES-256) is enabled by default
- [ ] Public access is blocked at the bucket level (Gold layer is served via CloudFront, not direct S3 access)
- [ ] Lifecycle rules are configured: Bronze and Silver objects transition to S3 Infrequent Access after 90 days
- [ ] Lifecycle rules are configured: Bronze objects older than 365 days transition to Glacier Deep Archive
- [ ] A CORS policy allows GET requests from the catch-app frontend domain (configurable via Terraform variable)
- [ ] Bucket tags include `Project=catch-data`, `Environment={env}`, `ManagedBy=terraform`
- [ ] All Terraform changes pass `terraform validate` and `terraform plan` without errors
- [ ] Infrastructure is documented in `infrastructure/README.md`

## Implementation Notes

**🤑 FinOps Miser notes:**

- S3 Standard storage: ~$0.023/GB/month. Total pipeline data for a season is
  estimated at <500 MB. Annual storage cost: ~$0.14/year for Standard tier.
- S3 IA storage (after 90 days): ~$0.0125/GB/month — nearly half the cost.
  Historical seasons rarely need fast access.
- Glacier Deep Archive (after 365 days): ~$0.00099/GB/month. Old Bronze data
  is preserved for analysis but almost never accessed.
- Lifecycle rules are the primary cost optimization lever for S3. Set them
  aggressively.

**🔧 Data Pipeline Janitor notes:**

- Versioning is critical: if a nightly run corrupts a Gold file, the previous
  version is automatically preserved and can be restored.
- Consider adding a bucket policy that denies `s3:DeleteObject` from all
  principals except the Terraform role. This protects Bronze data immutability.
- The CORS policy should be narrow: allow only the catch-app domain(s), not
  `*`. Use a Terraform variable for the domain so it can differ between
  environments.

**😴 Lazy Maintainer notes:**

- Lifecycle transitions are fully automated by AWS. No maintenance needed.
- Versioning + lifecycle means old versions are also transitioned. Consider
  adding a lifecycle rule to delete noncurrent versions after 30 days to
  prevent version bloat.

Update `infrastructure/variables.tf` to add any new variables (e.g.,
`cors_allowed_origins`). Update `infrastructure/main.tf` to modify the existing
S3 bucket resource.

Reference ADR-015 (AWS), ADR-016 (Terraform).
