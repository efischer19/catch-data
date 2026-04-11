---
title: "ADR-017: GitHub OIDC for AWS Authentication"
status: "Accepted"
date: "2026-04-04"
tags:
  - "ci-cd"
  - "aws"
  - "security"
  - "authentication"
---

## Context

* **Problem:** CI/CD workflows need to authenticate to AWS to deploy
  infrastructure (Terraform), push container images (ECR), and manage
  cloud resources. Storing long-lived AWS access keys as GitHub
  secrets is a security risk — keys can leak, are difficult to
  rotate, and grant broad, persistent access.
* **Constraints:** The authentication mechanism must work with GitHub
  Actions, support least-privilege IAM policies, require no long-lived
  secrets, and be straightforward to configure for downstream projects.

## Decision

We will use **GitHub OIDC (OpenID Connect) federation** to
authenticate GitHub Actions workflows to AWS, eliminating the need
for long-lived AWS credentials.

### How It Works

1. GitHub Actions issues a short-lived OIDC token for each workflow
   run, signed by GitHub's OIDC provider.
2. AWS IAM is configured with an **OIDC identity provider** that
   trusts GitHub's token issuer
   (`https://token.actions.githubusercontent.com`).
3. An **IAM role** with a trust policy scoped to the repository (and
   optionally branch or environment) allows the workflow to assume
   the role.
4. The `aws-actions/configure-aws-credentials` GitHub Action
   exchanges the OIDC token for temporary AWS credentials
   (STS AssumeRoleWithWebIdentity).

### Key Conventions

* **No long-lived AWS access keys** in GitHub Secrets. All AWS
  authentication uses OIDC federation.
* The IAM role ARN is stored as a GitHub Actions secret or variable
  (`AWS_ROLE_ARN`), but this is not a credential — it is a resource
  identifier.
* Trust policies should be scoped to the specific repository:

  ```json
  {
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:{{GITHUB_OWNER}}/{{PROJECT_NAME}}:*"
      }
    }
  }
  ```

* Use `id-token: write` permission in workflow jobs that need AWS
  credentials.
* Use placeholder values (`{{AWS_ROLE_ARN}}`, `{{AWS_REGION}}`) in
  workflow files — never commit real ARNs.

### Workflow Usage Pattern

```yaml
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
```

## Considered Options

1. **GitHub OIDC federation (Chosen):** Short-lived, automatically
   rotated credentials via OIDC token exchange.
    * *Pros:* No long-lived secrets to manage or rotate. Credentials
      are scoped to individual workflow runs. Trust policies can
      restrict access by repository, branch, and environment.
      Industry best practice recommended by both GitHub and AWS.
    * *Cons:* Requires one-time IAM OIDC provider setup in the AWS
      account. Slightly more complex initial configuration compared
      to static keys.
2. **Long-lived IAM access keys in GitHub Secrets:** Store
   `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as repository
   secrets.
    * *Pros:* Simple to set up initially.
    * *Cons:* Keys do not expire automatically. Rotation is manual
      and error-prone. If leaked, keys grant persistent access until
      revoked. Does not follow least-privilege best practices.
3. **Self-hosted runners with instance profiles:** Run GitHub Actions
   on EC2 instances with IAM roles attached.
    * *Pros:* No credentials in GitHub at all.
    * *Cons:* Requires maintaining self-hosted runner infrastructure.
      Significantly increases operational overhead for a template
      repository.

## Consequences

* **Positive:** Eliminates the risk of leaked long-lived credentials.
  Credentials are automatically scoped and short-lived. Follows AWS
  and GitHub security best practices. Easy to audit — trust policies
  explicitly list which repositories can assume which roles.
* **Negative:** Requires one-time setup of an IAM OIDC provider and
  trust policy in the target AWS account. Downstream projects must
  complete this setup before CI/CD workflows can authenticate.
* **Future Implications:** All CI/CD workflows that interact with
  AWS (Terraform plan/apply, ECR push, Lambda deployment) use this
  authentication pattern. See [ADR-015](ADR-015-aws_cloud_provider.md)
  for cloud provider choice and
  [ADR-016](ADR-016-terraform_iac.md) for infrastructure management.
