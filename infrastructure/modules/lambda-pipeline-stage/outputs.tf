output "ecr_repository_name" {
  description = "Name of the ECR repository for this pipeline stage"
  value       = aws_ecr_repository.this.name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository for this pipeline stage"
  value       = aws_ecr_repository.this.repository_url
}

output "lambda_function_name" {
  description = "Name of the Lambda function for this pipeline stage"
  value       = aws_lambda_function.this.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function for this pipeline stage"
  value       = aws_lambda_function.this.arn
}

output "lambda_execution_role_name" {
  description = "Name of the IAM role used by the Lambda function"
  value       = aws_iam_role.this.name
}

output "lambda_execution_role_arn" {
  description = "ARN of the IAM role used by the Lambda function"
  value       = aws_iam_role.this.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group for the Lambda function"
  value       = aws_cloudwatch_log_group.this.name
}
