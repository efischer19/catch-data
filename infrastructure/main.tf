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
  gold_ttl_seconds       = 3600 # 1 hour — balance between freshness and CDN efficiency
  use_custom_certificate = var.acm_certificate_arn != ""
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

  project_name   = var.project_name
  name           = "catch-analytics"
  environment    = var.environment
  s3_bucket_name = aws_s3_bucket.data.id
  s3_bucket_arn  = aws_s3_bucket.data.arn
  image_tag      = var.catch_analytics_image_tag
  memory_size    = 256
  timeout        = 120
  read_prefixes  = ["silver"]
  write_prefixes = ["gold"]
  environment_variables = {
    CLOUDFRONT_DISTRIBUTION_ID = aws_cloudfront_distribution.gold.id
  }
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

# -----------------------------------------------------------------------------
# CloudFront Distribution — Gold layer public access
# -----------------------------------------------------------------------------
# Serves Gold-layer JSON files from S3 to the catch-app frontend via a CDN.
# An Origin Access Control (OAC) policy ensures the S3 bucket remains private;
# only CloudFront can read Gold files.  See ADR-019.
# -----------------------------------------------------------------------------

resource "aws_cloudfront_origin_access_control" "gold" {
  name                              = "catch-data-gold-${var.environment}"
  description                       = "OAC restricting S3 Gold layer access to CloudFront only"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_cache_policy" "gold" {
  name        = "catch-data-gold-${var.environment}"
  comment     = "1-hour TTL cache policy for Gold layer JSON files"
  default_ttl = local.gold_ttl_seconds
  max_ttl     = local.gold_ttl_seconds
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }
    headers_config {
      header_behavior = "none"
    }
    query_strings_config {
      query_string_behavior = "none"
    }
    enable_accept_encoding_gzip   = true
    enable_accept_encoding_brotli = true
  }
}

resource "aws_cloudfront_response_headers_policy" "gold" {
  count = length(var.cors_allowed_origins) > 0 ? 1 : 0

  name    = "catch-data-gold-cors-${var.environment}"
  comment = "CORS response headers for Gold layer CDN — allows catch-app origins"

  cors_config {
    access_control_allow_credentials = false

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET", "HEAD"]
    }

    access_control_allow_origins {
      items = var.cors_allowed_origins
    }

    origin_override = true
  }
}

resource "aws_cloudfront_distribution" "gold" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "Gold layer CDN for catch-data ${var.environment}"
  price_class     = "PriceClass_100"

  aliases = var.cloudfront_custom_domain != "" ? [var.cloudfront_custom_domain] : []

  origin {
    domain_name              = aws_s3_bucket.data.bucket_regional_domain_name
    origin_id                = "S3-gold-${var.environment}"
    origin_path              = "/gold"
    origin_access_control_id = aws_cloudfront_origin_access_control.gold.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-gold-${var.environment}"

    cache_policy_id            = aws_cloudfront_cache_policy.gold.id
    response_headers_policy_id = length(var.cors_allowed_origins) > 0 ? aws_cloudfront_response_headers_policy.gold[0].id : null

    compress               = true
    viewer_protocol_policy = "redirect-to-https"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = !local.use_custom_certificate
    acm_certificate_arn            = local.use_custom_certificate ? var.acm_certificate_arn : null
    ssl_support_method             = local.use_custom_certificate ? "sni-only" : null
    minimum_protocol_version       = local.use_custom_certificate ? "TLSv1.2_2021" : null
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_policy" "data" {
  bucket = aws_s3_bucket.data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOACGoldAccess"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.data.arn}/gold/*"
        Condition = {
          StringEquals = {
            "aws:SourceArn" = aws_cloudfront_distribution.gold.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.data]
}

resource "aws_iam_role_policy" "analytics_cloudfront_invalidation" {
  name = "catch-analytics-cloudfront-${var.environment}"
  role = module.catch_analytics.lambda_execution_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = [aws_cloudfront_distribution.gold.arn]
      }
    ]
  })
}
