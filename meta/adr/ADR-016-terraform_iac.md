---
title: "ADR-016: Terraform for Infrastructure as Code"
status: "Accepted"
date: "2026-04-04"
tags:
  - "infrastructure"
  - "terraform"
  - "iac"
---

## Context

* **Problem:** Cloud infrastructure must be defined, versioned, and
  deployed in a repeatable way. Manual provisioning via the AWS
  Console is error-prone, unauditable, and impossible to reproduce
  across environments.
* **Constraints:** The IaC tool must support AWS resources (Lambda,
  ECR, S3, IAM), integrate with GitHub Actions CI/CD pipelines, and
  be approachable for contributors who may not be infrastructure
  specialists.

## Decision

We will use **Terraform** (by HashiCorp) to define and manage all AWS
infrastructure as code.

### Key Conventions

* All Terraform configuration lives in the `infrastructure/`
  directory at the repository root.
* Use **HCL (HashiCorp Configuration Language)** for all `.tf` files.
* Organize configuration into logical files:
  * `main.tf` — Primary resource definitions
  * `variables.tf` — Input variable declarations
  * `outputs.tf` — Output value declarations
  * `providers.tf` — Provider configuration (AWS)
  * `backend.tf` — State backend configuration (S3 + DynamoDB)
* Use a `modules/` subdirectory for reusable Terraform modules.
* **Remote state** is stored in S3 with DynamoDB locking. The backend
  configuration uses placeholder values that downstream projects must
  replace.
* Use `terraform plan` in CI to preview changes on pull requests.
* Use `terraform apply` only from the `main` branch or via manual
  dispatch.
* Pin the Terraform version and AWS provider version for
  reproducibility.
* Use placeholder values (`{{AWS_ACCOUNT_ID}}`, `{{AWS_REGION}}`,
  `{{TF_STATE_BUCKET}}`, `{{TF_LOCK_TABLE}}`) — never commit real
  resource identifiers.

### Directory Structure

```text
infrastructure/
├── main.tf          # Primary resource definitions
├── variables.tf     # Input variables
├── outputs.tf       # Output values
├── providers.tf     # AWS provider configuration
├── backend.tf       # Remote state backend (S3 + DynamoDB)
└── modules/         # Reusable Terraform modules
    └── README.md
```

## Considered Options

1. **Terraform (Chosen):** Declarative IaC tool with broad provider
   support.
    * *Pros:* Cloud-agnostic (supports AWS, GCP, Azure), large
      community, mature module ecosystem, plan/apply workflow enables
      safe reviews, HCL is readable and approachable.
    * *Cons:* State management adds operational complexity. HCL is a
      domain-specific language (not Python). HashiCorp license change
      (BSL) may concern some teams.
2. **AWS CloudFormation:** AWS-native IaC service.
    * *Pros:* No state file to manage, deep AWS integration.
    * *Cons:* AWS-only, verbose YAML/JSON syntax, slower feedback
      loops, limited module/reuse patterns.
3. **AWS CDK (Cloud Development Kit):** Define infrastructure in
   Python (or other languages).
    * *Pros:* Uses Python (matches our stack), full programming
      language constructs.
    * *Cons:* Generates CloudFormation under the hood, adds
      abstraction layers, less transparent than HCL, smaller
      community for troubleshooting.
4. **Pulumi:** IaC using general-purpose languages (Python, TypeScript).
    * *Pros:* Write infrastructure in Python, strong typing.
    * *Cons:* Smaller community than Terraform, commercial backing
      model, fewer published modules.

## Consequences

* **Positive:** Infrastructure changes are version-controlled,
  reviewable, and reproducible. The plan/apply workflow gives
  contributors a preview of changes before they are applied.
  Terraform's module system encourages reusable, composable
  infrastructure.
* **Negative:** Contributors need to learn HCL in addition to Python.
  State management (S3 backend, locking) adds operational overhead.
  The Terraform binary must be installed locally and in CI.
* **Future Implications:** CI/CD workflows include `terraform plan`
  on PRs and `terraform apply` on merges to `main`. Downstream
  projects add environment-specific variable files (e.g.,
  `terraform.tfvars`) and extend the module library. See
  [ADR-015](ADR-015-aws_cloud_provider.md) for cloud provider choice
  and [ADR-017](ADR-017-github_oidc_aws_auth.md) for CI/CD
  authentication.
