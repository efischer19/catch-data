# AWS provider configuration for {{PROJECT_NAME}}
# See ADR-015 (AWS as Cloud Provider)
#
# Version constraints are defined in versions.tf.

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}
