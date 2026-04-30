variable "project_name" {
  description = "Project name used for tagging"
  type        = string
}

variable "name" {
  description = "Base resource name for the pipeline stage"
  type        = string
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

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
}

variable "read_prefixes" {
  description = "Bucket prefixes the Lambda can read from, without trailing /*"
  type        = list(string)
}

variable "write_prefixes" {
  description = "Bucket prefixes the Lambda can write to, without trailing /*"
  type        = list(string)
}

variable "environment_variables" {
  description = "Additional Lambda environment variables"
  type        = map(string)
  default     = {}
}
