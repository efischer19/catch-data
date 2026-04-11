---
title: "ADR-015: AWS as Cloud Provider"
status: "Accepted"
date: "2026-04-04"
tags:
  - "cloud"
  - "aws"
  - "infrastructure"
---

## Context

* **Problem:** This project needs a cloud platform for deploying data
  pipelines, serverless functions, container workloads, and object
  storage. The choice of cloud provider affects every downstream
  decision — from infrastructure tooling to CI/CD integration to
  runtime APIs.
* **Constraints:** The provider must offer mature services for Lambda
  (serverless compute), ECR (container image registry), S3 (object
  storage), and IAM (identity and access management). It must
  integrate well with GitHub Actions for CI/CD and support
  Infrastructure as Code tooling.

## Decision

We will use **Amazon Web Services (AWS)** as the cloud provider for
all infrastructure and deployment targets in this project.

### Key Conventions

* All cloud resources are provisioned in AWS.
* Use **AWS Lambda** for serverless compute workloads.
* Use **Amazon ECR** for storing Docker container images.
* Use **Amazon S3** for object and data storage.
* Use **AWS IAM** for access control and service permissions.
* **No hard-coded credentials.** All authentication uses IAM roles,
  environment variables, or GitHub OIDC federation
  (see [ADR-017](ADR-017-github_oidc_aws_auth.md)).
* Use `boto3` as the Python SDK for interacting with AWS services.
* Use placeholder values (`{{AWS_ACCOUNT_ID}}`, `{{AWS_REGION}}`,
  `{{S3_BUCKET_NAME}}`) throughout configuration — never commit real
  account IDs, ARNs, or resource names.

### AWS Services in Use

| Service | Purpose |
| :--- | :--- |
| Lambda | Serverless function execution |
| ECR | Container image registry |
| S3 | Object / data storage |
| IAM | Identity and access management |
| CloudWatch | Logging and monitoring |

## Considered Options

1. **AWS (Chosen):** The most widely adopted cloud platform with the
   broadest service catalog.
    * *Pros:* Mature ecosystem, extensive documentation, strong Python
      SDK (`boto3`), broad CI/CD integration, industry-standard IAM
      model, large community.
    * *Cons:* Complex pricing model. Vendor lock-in for AWS-specific
      services (Lambda, ECR, S3).
2. **Google Cloud Platform (GCP):** Google's cloud offering.
    * *Pros:* Strong data and ML tooling, competitive pricing.
    * *Cons:* Smaller ecosystem for general-purpose workloads. Less
      mature IAM model compared to AWS.
3. **Microsoft Azure:** Microsoft's cloud platform.
    * *Pros:* Strong enterprise integration, good hybrid cloud story.
    * *Cons:* Python SDK is less ergonomic than `boto3`. Naming
      conventions and service catalog are harder to navigate.

## Consequences

* **Positive:** AWS provides a mature, well-documented platform for
  every service this project requires. The `boto3` SDK is idiomatic
  Python and well-maintained. GitHub OIDC federation eliminates the
  need for long-lived credentials.
* **Negative:** Tight coupling to AWS services. Migrating to another
  provider would require significant rework of infrastructure code,
  deployment workflows, and application code that uses `boto3`.
* **Future Implications:** All infrastructure is defined with
  Terraform (see [ADR-016](ADR-016-terraform_iac.md)). CI/CD
  workflows authenticate to AWS via GitHub OIDC
  (see [ADR-017](ADR-017-github_oidc_aws_auth.md)). Downstream
  projects should replace placeholder values with real AWS resource
  identifiers.
