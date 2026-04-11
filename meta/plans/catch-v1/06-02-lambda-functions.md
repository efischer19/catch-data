Title: feat: Terraform Lambda functions for Silver and Gold processing

## What do you want to build?

Define Terraform resources for the two AWS Lambda functions that power the
Silver and Gold pipeline layers. Each Lambda is deployed as a Docker container
image from ECR and has specific memory, timeout, and environment variable
configurations tailored to its workload.

## Acceptance Criteria

- [ ] A `catch-processing` Lambda function is defined for Silver layer processing
- [ ] A `catch-analytics` Lambda function is defined for Gold layer generation
- [ ] Both Lambdas use container image packaging (ECR image URI)
- [ ] `catch-processing` Lambda: 512 MB memory, 300-second timeout
- [ ] `catch-analytics` Lambda: 256 MB memory, 120-second timeout (lighter workload)
- [ ] Both Lambdas have environment variables: `ENVIRONMENT`, `S3_BUCKET_NAME`, `LOG_FORMAT=json`
- [ ] Each Lambda has its own IAM execution role with least-privilege permissions
- [ ] ECR repositories are defined for both Lambda container images
- [ ] ECR lifecycle policies retain only the last 10 untagged images
- [ ] All Terraform changes pass `terraform validate` and `terraform plan`
- [ ] Lambda configurations are documented in `infrastructure/README.md`

## Implementation Notes

**🤑 FinOps Miser notes:**

- Lambda pricing is per-invocation and per-GB-second. At 1 invocation/night:
  - Silver (512 MB × 60s typical): ~$0.0005/run → ~$0.18/year
  - Gold (256 MB × 30s typical): ~$0.0001/run → ~$0.04/year
  - Total Lambda cost: ~$0.22/year. Effectively free.
- Start with these memory settings and monitor via CloudWatch. If actual
  memory usage is much lower, reduce the allocation.
- ECR storage: ~$0.10/GB/month. Docker images for Python Lambda are typically
  200-400 MB. With 10-image retention, cost is ~$0.40/month. Consider reducing
  retention to 5 images if cost becomes noticeable.

**🔧 Data Pipeline Janitor notes:**

- Use separate IAM roles for each Lambda. The Silver Lambda needs
  `s3:GetObject` on `bronze/*` and `s3:PutObject` on `silver/*`. The Gold
  Lambda needs `s3:GetObject` on `silver/*` and `s3:PutObject` on `gold/*`.
  Neither should have broader permissions.
- Pin Lambda runtime to a specific ECR image tag (not `latest`) for
  reproducible deployments. Use the git SHA or semantic version as the tag.

**😴 Lazy Maintainer notes:**

- Lambda functions are managed entirely by AWS — no servers to patch, no
  scaling to configure. The only maintenance is deploying new container
  images when the processing logic changes.
- Consider adding Lambda function aliases (e.g., `live`) to enable blue/green
  deployments. This is optional for V1 but architecturally clean.

Terraform resources:

- `aws_lambda_function` × 2
- `aws_iam_role` × 2 (separate execution roles)
- `aws_iam_role_policy_attachment` for basic Lambda execution
- `aws_iam_policy` for S3 access (scoped per Lambda)
- `aws_ecr_repository` × 2
- `aws_ecr_lifecycle_policy` × 2

Consider creating a Terraform module under `infrastructure/modules/lambda-pipeline-stage/`
to avoid duplicating the Lambda + IAM + ECR pattern. Reference ADR-016.
