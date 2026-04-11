# Version constraints for {{PROJECT_NAME}} infrastructure
# See ADR-016 (Terraform for IaC)
#
# Pin Terraform and provider versions for reproducible builds.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
