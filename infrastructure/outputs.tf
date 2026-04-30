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

output "cloudfront_distribution_domain" {
  description = "Domain name of the CloudFront distribution serving the Gold layer"
  value       = aws_cloudfront_distribution.gold.domain_name
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution serving the Gold layer (used for cache invalidation)"
  value       = aws_cloudfront_distribution.gold.id
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions OIDC IAM role used by CI/CD workflows"
  value       = aws_iam_role.github_actions.arn
}

output "ingestion_user_name" {
  description = "Name of the IAM user for the Mac Mini ingestion script (Bronze writes only)"
  value       = aws_iam_user.ingestion.name
}

output "sns_pipeline_alerts_topic_arn" {
  description = "ARN of the SNS topic that receives pipeline failure alerts"
  value       = aws_sns_topic.pipeline_alerts.arn
}
