# Output values for {{PROJECT_NAME}} infrastructure
# These values are useful for configuring applications and CI/CD pipelines.

output "s3_bucket_name" {
  description = "Name of the S3 data bucket"
  value       = aws_s3_bucket.data.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 data bucket"
  value       = aws_s3_bucket.data.arn
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.app.repository_url
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.app.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.app.arn
}

output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution IAM role"
  value       = aws_iam_role.lambda_execution.arn
}
