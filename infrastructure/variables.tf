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

variable "cors_allowed_origins" {
  description = "Frontend origins allowed to read Gold-layer objects via S3 CORS"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for origin in var.cors_allowed_origins :
      origin != "*" && can(regex("^https?://", origin))
    ])
    error_message = "CORS origins must be explicit http(s) URLs and may not use '*'."
  }
}
