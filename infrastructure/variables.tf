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

variable "catch_processing_image_tag" {
  description = "Pinned ECR image tag for the catch-processing Lambda container"
  type        = string
  default     = "bootstrap"

  validation {
    condition     = trimspace(var.catch_processing_image_tag) != "" && var.catch_processing_image_tag != "latest"
    error_message = "catch_processing_image_tag must be a non-empty pinned tag and may not be 'latest'."
  }
}

variable "catch_analytics_image_tag" {
  description = "Pinned ECR image tag for the catch-analytics Lambda container"
  type        = string
  default     = "bootstrap"

  validation {
    condition     = trimspace(var.catch_analytics_image_tag) != "" && var.catch_analytics_image_tag != "latest"
    error_message = "catch_analytics_image_tag must be a non-empty pinned tag and may not be 'latest'."
  }
}

variable "cloudfront_custom_domain" {
  description = "Optional custom domain name for the CloudFront distribution (e.g., cdn.example.com). Requires acm_certificate_arn."
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "Optional ACM certificate ARN for the custom CloudFront domain. Must be issued in us-east-1. Required when cloudfront_custom_domain is set."
  type        = string
  default     = ""
}
