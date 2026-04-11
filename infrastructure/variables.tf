# Input variables for {{PROJECT_NAME}} infrastructure
# See ADR-016 (Terraform for IaC)
#
# Replace default values with your project-specific configuration.

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "{{PROJECT_NAME}}"
}

variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "{{AWS_REGION}}"
}
