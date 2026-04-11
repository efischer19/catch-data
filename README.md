# python-aws-data-blueprint

> A template for Python + AWS data projects: Lambda deployment, ECR image
> management, S3 data storage, and Terraform infrastructure — all wired into a
> monorepo with Poetry, pytest, and Ruff.

## What Is This?

This is a **GitHub template repository** for bootstrapping Python data projects
that deploy to AWS. It extends the
[python-project-blueprint](https://github.com/efischer19/python-project-blueprint)
monorepo pattern with AWS integration: serverless Lambda functions, ECR
container images, S3 object storage, and Terraform infrastructure scaffolding.

Built on the [blueprint-repo-blueprints](https://github.com/efischer19/blueprint-repo-blueprints)
foundation, this template adds everything needed to go from "empty repo" to
"deployed data pipeline" as a fill-in-the-blanks exercise.

## How to Use This Template

1. Click the **"Use this template"** button at the top of the repository
   page on GitHub.
2. Choose a name for your new repository.
3. Clone your new repository and replace all `{{...}}` placeholders
   (see [Replace Template Placeholders](#1-replace-template-placeholders) below).

For more details on GitHub template repositories, see the
[official documentation](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository).

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

See `meta/adr/` for the full list of Architecture Decision Records.

### Key Files

* **`LICENSE.md`** — MIT License
* **`CODE_OF_CONDUCT.md`** — Contributor Covenant Code of Conduct
* **`SECURITY.md`** — Security policy and vulnerability reporting
* **`CONTRIBUTING.md`** — Guidelines for contributing to the project
* **`.python-version`** — Python version specification (3.12)

## Getting Started

After creating a new repository from this template:

### 1. Replace Template Placeholders

Search the repository for the following placeholders and replace them with
values appropriate for your project:

| Placeholder | Description | Example |
| :--- | :--- | :--- |
| `{{PROJECT_NAME}}` | Your repository / project name | `my-data-project` |
| `{{GITHUB_OWNER}}` | GitHub username or organization | `my-org` |
| `{{APP_NAME}}` | Application directory name (in `apps/`) | `data-pipeline` |
| `{{LIB_NAME}}` | Library directory name (in `libs/`) | `core-utils` |
| `{{AWS_ACCOUNT_ID}}` | Your AWS account ID | `123456789012` |
| `{{AWS_REGION}}` | Target AWS region | `us-east-1` |
| `{{AWS_ROLE_ARN}}` | IAM role ARN for GitHub OIDC | `arn:aws:iam::123456789012:role/github-actions` |
| `{{TF_STATE_BUCKET}}` | S3 bucket for Terraform state | `my-project-tf-state` |
| `{{TF_LOCK_TABLE}}` | DynamoDB table for state locking | `my-project-tf-lock` |
| `{{S3_BUCKET_NAME}}` | S3 bucket for application data | `my-project-data` |

### 2. Set Up Local Development

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

### 3. Set Up AWS Infrastructure

```bash
# Install Terraform (https://developer.hashicorp.com/terraform/install)

# Initialize Terraform (after replacing placeholders in infrastructure/)
cd infrastructure
terraform init
terraform plan
terraform apply
```

### 4. Create Your First Application

```bash
mkdir -p apps/my-app
cd apps/my-app
poetry init
mkdir -p src/my_app tests
```

### 5. Verify CI

Push a change or open a pull request to confirm the CI workflow runs and
passes in your new repository.

## Design Principles

* **Python 3.12+ only.** Take advantage of modern Python features and
  performance improvements.
* **Poetry everywhere.** Consistent dependency management across all apps
  and libraries.
* **Ruff for speed.** Fast linting and formatting that replaces multiple
  tools.
* **AWS-native.** Lambda, ECR, S3, and IAM as the deployment target.
* **Infrastructure as Code.** All AWS resources defined in Terraform.
* **No secrets in source.** OIDC federation for CI/CD, placeholder values
  for all identifiers.
* **Documentation-first.** Every significant decision is captured in an ADR.
* **AI-friendly.** The structure and conventions are designed to work well
  with AI-assisted development workflows.

## License

This project is licensed under the [MIT License](./LICENSE.md).
