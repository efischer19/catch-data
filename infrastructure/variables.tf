# Input variables for catch-data infrastructure
# See ADR-016 (Terraform for IaC)

variable "project_name" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "catch-data"
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
  default     = "us-west-2"
}
