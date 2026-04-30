# Terraform configuration for catch-data
# See ADR-015 (AWS as Cloud Provider) and ADR-016 (Terraform for IaC)

# -----------------------------------------------------------------------------
# S3 Bucket — Data storage (Medallion Architecture)
# -----------------------------------------------------------------------------
# This bucket stores all pipeline data using key prefixes to separate the
# medallion layers (see ADR-018). The recommended key layout is:
#
#   s3://catch-data-{env}/
#   ├── bronze/{source}/{YYYY-MM-DD}/       # Raw ingested data
#   ├── silver/{entity}/{YYYY-MM-DD}/       # Cleaned & validated data
#   └── gold/served/{metric_name}/          # Business-ready aggregations
#
# A single bucket with key prefixes is preferred over separate buckets for
# simplicity. IAM policies can restrict access per prefix if needed.
# -----------------------------------------------------------------------------
locals {
  data_bucket_name                     = "catch-data-${var.environment}"
  seconds_per_day                      = 24 * 60 * 60
  silver_processing_dlq_retention_days = 14
  # SQS supports up to 14 days of message retention; keep failed Silver events
  # available for the full window to maximize replay/debugging time.
  silver_processing_dlq_retention_seconds = (
    local.silver_processing_dlq_retention_days * local.seconds_per_day
  )
}

resource "aws_s3_bucket" "data" {
  bucket = local.data_bucket_name

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

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "bronze-tiering"
    status = "Enabled"

    filter {
      prefix = "bronze/"
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }
  }

  rule {
    id     = "silver-tiering"
    status = "Enabled"

    filter {
      prefix = "silver/"
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "data" {
  count  = length(var.cors_allowed_origins) > 0 ? 1 : 0
  bucket = aws_s3_bucket.data.id

  cors_rule {
    allowed_headers = []
    allowed_methods = ["GET"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_sqs_queue" "silver_processing_dlq" {
  name                      = "${var.project_name}-silver-dlq-${var.environment}"
  message_retention_seconds = local.silver_processing_dlq_retention_seconds

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

module "catch_processing" {
  source = "./modules/lambda-pipeline-stage"

  project_name   = var.project_name
  name           = "catch-processing"
  environment    = var.environment
  s3_bucket_name = aws_s3_bucket.data.id
  s3_bucket_arn  = aws_s3_bucket.data.arn
  image_tag      = var.catch_processing_image_tag
  memory_size    = 512
  timeout        = 300
  read_prefixes  = ["bronze"]
  write_prefixes = ["silver"]
  environment_variables = {
    SILVER_DLQ_URL = aws_sqs_queue.silver_processing_dlq.url
  }
}

module "catch_analytics" {
  source = "./modules/lambda-pipeline-stage"

  project_name          = var.project_name
  name                  = "catch-analytics"
  environment           = var.environment
  s3_bucket_name        = aws_s3_bucket.data.id
  s3_bucket_arn         = aws_s3_bucket.data.arn
  image_tag             = var.catch_analytics_image_tag
  memory_size           = 256
  timeout               = 120
  read_prefixes         = ["silver"]
  write_prefixes        = ["gold"]
  environment_variables = {}
}

resource "aws_iam_role_policy" "processing_dlq_access" {
  name = "catch-processing-dlq-${var.environment}"
  role = module.catch_processing.lambda_execution_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.silver_processing_dlq.arn
        ]
      }
    ]
  })
}

resource "aws_lambda_permission" "allow_data_bucket_invoke_catch_processing" {
  statement_id  = "AllowExecutionFromDataBucketCatchProcessing"
  action        = "lambda:InvokeFunction"
  function_name = module.catch_processing.lambda_function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data.arn
}

resource "aws_lambda_permission" "allow_data_bucket_invoke_catch_analytics" {
  statement_id  = "AllowExecutionFromDataBucketCatchAnalytics"
  action        = "lambda:InvokeFunction"
  function_name = module.catch_analytics.lambda_function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.data.arn
}

resource "aws_s3_bucket_notification" "pipeline_triggers" {
  bucket = aws_s3_bucket.data.id

  lambda_function {
    lambda_function_arn = module.catch_processing.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "bronze/schedule_"
  }

  lambda_function {
    lambda_function_arn = module.catch_analytics.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "silver/master_schedule_"
  }

  depends_on = [
    aws_lambda_permission.allow_data_bucket_invoke_catch_processing,
    aws_lambda_permission.allow_data_bucket_invoke_catch_analytics,
  ]
}
