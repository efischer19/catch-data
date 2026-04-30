# Output values for catch-data infrastructure
# These values are useful for configuring applications and CI/CD pipelines.

output "s3_bucket_name" {
  description = "Name of the S3 data bucket"
  value       = aws_s3_bucket.data.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 data bucket"
  value       = aws_s3_bucket.data.arn
}

output "catch_processing_ecr_repository_url" {
  description = "URL of the catch-processing ECR repository"
  value       = module.catch_processing.ecr_repository_url
}

output "catch_analytics_ecr_repository_url" {
  description = "URL of the catch-analytics ECR repository"
  value       = module.catch_analytics.ecr_repository_url
}

output "catch_processing_lambda_function_name" {
  description = "Name of the catch-processing Lambda function"
  value       = module.catch_processing.lambda_function_name
}

output "catch_processing_lambda_function_arn" {
  description = "ARN of the catch-processing Lambda function"
  value       = module.catch_processing.lambda_function_arn
}

output "catch_processing_lambda_execution_role_arn" {
  description = "ARN of the catch-processing Lambda execution IAM role"
  value       = module.catch_processing.lambda_execution_role_arn
}

output "catch_analytics_lambda_function_name" {
  description = "Name of the catch-analytics Lambda function"
  value       = module.catch_analytics.lambda_function_name
}

output "catch_analytics_lambda_function_arn" {
  description = "ARN of the catch-analytics Lambda function"
  value       = module.catch_analytics.lambda_function_arn
}

output "catch_analytics_lambda_execution_role_arn" {
  description = "ARN of the catch-analytics Lambda execution IAM role"
  value       = module.catch_analytics.lambda_execution_role_arn
}
