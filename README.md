# catch-data

> MLB baseball catch data pipeline: ingesting, processing, and serving
> game statistics via a Bronze/Silver/Gold medallion architecture on AWS.

## What Is This?

**catch-data** is a Python + AWS data project that collects MLB baseball
statistics from the [MLB Stats API](https://statsapi.mlb.com) and
processes them through a medallion data pipeline deployed to AWS Lambda,
S3, and CloudFront.

Built on the
[python-aws-data-blueprint](https://github.com/efischer19/python-aws-data-blueprint)
monorepo pattern with AWS integration: serverless Lambda functions, ECR
container images, S3 object storage, and Terraform infrastructure.

## What's Included

| Path | Purpose |
| :--- | :--- |
| `apps/` | Standalone Python applications, each with its own `pyproject.toml` |
| `libs/` | Shared Python libraries used across applications |
| `infrastructure/` | Terraform configuration for AWS resources (S3, ECR, Lambda, IAM) |
| `testing/` | Shared test utilities, fixtures, and helpers |
| `scripts/` | Utility and automation scripts |
| `templates/` | Template files for scaffolding new apps and libs |
| `meta/adr/` | Architecture Decision Records — the logbook of *why* decisions were made |
| `meta/plans/` | Project plans and roadmaps |
| `docs-src/` | Source files for generated documentation (MkDocs) |
| `.github/` | GitHub-specific configuration (issue templates, PR templates, CI workflows) |

### Key Tooling Decisions (ADRs)

| ADR | Decision |
| :--- | :--- |
| [ADR-002](meta/adr/ADR-002-use_python312.md) | Python 3.12+ as minimum version |
| [ADR-003](meta/adr/ADR-003-use_poetry.md) | Poetry for dependency management |
| [ADR-004](meta/adr/ADR-004-use_pytest.md) | pytest for testing |
| [ADR-005](meta/adr/ADR-005-use_ruff.md) | Ruff for linting and formatting |
| [ADR-006](meta/adr/ADR-006-use_docker.md) | Docker for containerization |
| [ADR-007](meta/adr/ADR-007-monorepo_apps_structure.md) | Monorepo /apps structure |
| [ADR-015](meta/adr/ADR-015-aws_cloud_provider.md) | AWS as cloud provider |
| [ADR-016](meta/adr/ADR-016-terraform_iac.md) | Terraform for Infrastructure as Code |
| [ADR-017](meta/adr/ADR-017-github_oidc_aws_auth.md) | GitHub OIDC for AWS authentication |
| [ADR-018](meta/adr/ADR-018-medallion_architecture.md) | Bronze/Silver/Gold medallion architecture |

See `meta/adr/` for the full list of Architecture Decision Records.

### Key Files

* **`LICENSE.md`** — GPL License
* **`CODE_OF_CONDUCT.md`** — Contributor Covenant Code of Conduct
* **`SECURITY.md`** — Security policy and vulnerability reporting
* **`CONTRIBUTING.md`** — Guidelines for contributing to the project
* **`.python-version`** — Python version specification (3.12)

## Getting Started

### Set Up Local Development

```bash
# Install Python 3.12+ (use pyenv or your preferred method)
pyenv install 3.12
pyenv local 3.12

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run local quality checks
./scripts/local-ci-check.sh

# Build documentation (optional)
pip install -r docs-requirements.txt
./scripts/build-docs.sh
```

### Set Up AWS Infrastructure

```bash
# Install Terraform (https://developer.hashicorp.com/terraform/install)

# Initialize Terraform
cd infrastructure
terraform init
terraform plan
terraform apply
```

## Design Principles

* **Python 3.12+ only.** Take advantage of modern Python features and
  performance improvements.
* **Poetry everywhere.** Consistent dependency management across all apps
  and libraries.
* **Ruff for speed.** Fast linting and formatting that replaces multiple
  tools.
* **AWS-native.** Lambda, ECR, S3, and IAM as the deployment target.
* **Infrastructure as Code.** All AWS resources defined in Terraform.
* **No secrets in source.** OIDC federation for CI/CD.
* **Documentation-first.** Every significant decision is captured in an ADR.
* **AI-friendly.** The structure and conventions are designed to work well
  with AI-assisted development workflows.

## License

This project is licensed under the [MIT License](./LICENSE.md).
