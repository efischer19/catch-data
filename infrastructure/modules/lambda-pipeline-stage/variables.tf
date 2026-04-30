variable "project_name" {
  description = "Project name used for tagging"
  type        = string
}

variable "name" {
  description = "Base resource name for the pipeline stage"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]+([._-][a-z0-9]+)*$", var.name))
    error_message = "name must use lowercase letters, digits, dots, underscores, or hyphens in an AWS ECR-compatible format."
  }
}

variable "environment" {
  description = "Deployment environment suffix"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name exposed to the Lambda environment"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the shared medallion data bucket"
  type        = string
}

variable "image_tag" {
  description = "Pinned ECR image tag for reproducible Lambda deployments"
  type        = string
}

variable "untagged_image_retention_count" {
  description = "Number of untagged images to retain in the stage ECR repository"
  type        = number
  default     = 10

  validation {
    condition     = var.untagged_image_retention_count > 0
    error_message = "untagged_image_retention_count must be greater than zero."
  }
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
}

variable "read_prefixes" {
  description = "Bucket prefixes the Lambda can read from, without leading slashes or trailing /*"
  type        = list(string)

  validation {
    condition = alltrue([
      for prefix in var.read_prefixes :
      trimspace(prefix) != "" && !startswith(prefix, "/") && !endswith(prefix, "/") && !endswith(prefix, "/*")
    ])
    error_message = "read_prefixes entries must be non-empty prefixes without a trailing '/' or '/*'."
  }
}

variable "write_prefixes" {
  description = "Bucket prefixes the Lambda can write to, without leading slashes or trailing /*"
  type        = list(string)

  validation {
    condition = alltrue([
      for prefix in var.write_prefixes :
      trimspace(prefix) != "" && !startswith(prefix, "/") && !endswith(prefix, "/") && !endswith(prefix, "/*")
    ])
    error_message = "write_prefixes entries must be non-empty prefixes without a trailing '/' or '/*'."
  }
}

variable "environment_variables" {
  description = "Additional Lambda environment variables"
  type        = map(string)
  default     = {}
}
