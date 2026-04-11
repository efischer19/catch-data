# Terraform configuration for {{PROJECT_NAME}}
# See ADR-015 (AWS as Cloud Provider) and ADR-016 (Terraform for IaC)
#
# Replace all {{...}} placeholders with your project-specific values
# before running `terraform init` and `terraform plan`.

# -----------------------------------------------------------------------------
# S3 Bucket — Data storage (Medallion Architecture)
# -----------------------------------------------------------------------------
# This bucket stores all pipeline data using key prefixes to separate the
# medallion layers (see ADR-018). The recommended key layout is:
#
#   s3://{{PROJECT_NAME}}-data-{env}/
#   ├── bronze/{source}/{YYYY-MM-DD}/       # Raw ingested data
#   ├── silver/{entity}/{YYYY-MM-DD}/       # Cleaned & validated data
#   └── gold/served/{metric_name}/          # Business-ready aggregations
#
# A single bucket with key prefixes is preferred over separate buckets for
# simplicity. IAM policies can restrict access per prefix if needed.
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "data" {
  bucket = "{{PROJECT_NAME}}-data-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# ECR Repository — Container image registry
# -----------------------------------------------------------------------------
resource "aws_ecr_repository" "app" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# IAM Role — Lambda execution role
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data.arn,
          "${aws_s3_bucket.data.arn}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# Lambda Function — Serverless compute
# -----------------------------------------------------------------------------
resource "aws_lambda_function" "app" {
  function_name = "${var.project_name}-${var.environment}"
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  timeout       = 300
  memory_size   = 512

  environment {
    variables = {
      ENVIRONMENT    = var.environment
      S3_BUCKET_NAME = aws_s3_bucket.data.id
      LOG_FORMAT     = "json"
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
