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

# Current AWS account and region — used to construct explicit resource ARNs
# in IAM policies to avoid wildcard permissions.
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

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
      },
      # Belt-and-suspenders: explicitly deny the Silver Lambda from writing
      # to Bronze, enforcing the Bronze immutability guarantee at the bucket
      # policy layer in addition to the IAM role level.
      {
        Sid    = "DenySilverLambdaBronzeWrite"
        Effect = "Deny"
        Principal = {
          AWS = module.catch_processing.lambda_execution_role_arn
        }
        Action   = ["s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.data.arn}/bronze/*"
      },
      # Belt-and-suspenders: explicitly deny the Gold Lambda from writing to
      # Bronze or Silver, preserving the one-way data flow of the pipeline.
      {
        Sid    = "DenyGoldLambdaNonGoldWrite"
        Effect = "Deny"
        Principal = {
          AWS = module.catch_analytics.lambda_execution_role_arn
        }
        Action = ["s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.data.arn}/bronze/*",
          "${aws_s3_bucket.data.arn}/silver/*",
        ]
      },
      # Belt-and-suspenders: explicitly deny the ingestion IAM user from
      # reading Silver or Gold objects — ingest writes to Bronze only.
      {
        Sid    = "DenyIngestionSilverGoldAccess"
        Effect = "Deny"
        Principal = {
          AWS = aws_iam_user.ingestion.arn
        }
        Action = ["s3:GetObject"]
        Resource = [
          "${aws_s3_bucket.data.arn}/silver/*",
          "${aws_s3_bucket.data.arn}/gold/*",
        ]
      },
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

# -----------------------------------------------------------------------------
# Ingestion IAM user — Mac Mini script that writes raw data to Bronze
# -----------------------------------------------------------------------------
# This user has write-only access to the bronze/ prefix and no access to
# Silver or Gold layers, enforcing the principle of least privilege for the
# ingestion stage. Credentials are stored in ~/.aws/credentials on the Mac
# Mini and should be rotated periodically.
# -----------------------------------------------------------------------------

resource "aws_iam_user" "ingestion" {
  name = "${var.project_name}-ingestion-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_user_policy" "ingestion_s3" {
  name = "${var.project_name}-ingestion-s3-${var.environment}"
  user = aws_iam_user.ingestion.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "IngestBronzeWrite"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.data.arn}/bronze/*"
      },
      {
        Sid      = "IngestBronzeList"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data.arn
        Condition = {
          StringLike = {
            "s3:prefix" = ["bronze/*"]
          }
        }
      },
    ]
  })
}

# -----------------------------------------------------------------------------
# GitHub Actions OIDC role — CI/CD deployments via short-lived credentials
# -----------------------------------------------------------------------------
# See ADR-017 for the decision to use GitHub OIDC instead of long-lived keys.
# The trust policy restricts access to the configured GitHub repository using
# condition keys on the OIDC subject claim.
#
# Bootstrap note: this role must exist before GitHub Actions can assume it.
# On first deploy, create a temporary IAM role manually, run `terraform apply`
# to provision this role, then update the workflows to use this Terraform-
# managed role and remove the temporary bootstrap role. Alternatively, import
# an existing role with:
#   terraform import aws_iam_role.github_actions <role-name>
# -----------------------------------------------------------------------------

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # Thumbprints for token.actions.githubusercontent.com — see:
  # https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc_verify-thumbprint.html
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

resource "aws_iam_role" "github_actions" {
  # Name matches the role-to-assume ARN used in all workflow files:
  # arn:aws:iam::<account>:role/<project_name>-github-actions
  name        = "${var.project_name}-github-actions"
  description = "GitHub Actions CI/CD role assumed via OIDC federation"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubActionsOIDC"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github.arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            # Restrict to this repository only; workflows from other repos
            # cannot assume this role.
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_owner}/${var.github_repo}:*"
          }
        }
      }
    ]
  })

  tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}

# ECR authentication and image push (used by reusable-build-push.yml)
resource "aws_iam_role_policy" "github_actions_ecr" {
  name = "${var.project_name}-github-actions-ecr"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # GetAuthorizationToken has no resource-level restrictions in ECR.
        Sid      = "ECRAuthToken"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:ListImages",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/${var.project_name}-*"
      },
      {
        # Repository lifecycle management needed for Terraform to manage ECR
        # resources (e.g., scan settings, tag mutability, lifecycle policies).
        Sid    = "ECRManage"
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository",
          "ecr:DeleteRepository",
          "ecr:DeleteLifecyclePolicy",
          "ecr:GetLifecyclePolicy",
          "ecr:GetRepositoryPolicy",
          "ecr:ListTagsForResource",
          "ecr:PutImageScanningConfiguration",
          "ecr:PutImageTagMutability",
          "ecr:PutLifecyclePolicy",
          "ecr:SetRepositoryPolicy",
          "ecr:TagResource",
          "ecr:UntagResource",
        ]
        Resource = "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/${var.project_name}-*"
      },
    ]
  })
}

# Lambda function code updates and management (used by deploy.yml)
resource "aws_iam_role_policy" "github_actions_lambda" {
  name = "${var.project_name}-github-actions-lambda"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "LambdaDeploy"
        Effect = "Allow"
        Action = [
          "lambda:AddPermission",
          "lambda:CreateFunction",
          "lambda:DeleteFunction",
          "lambda:GetAlias",
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:GetPolicy",
          "lambda:ListAliases",
          "lambda:ListFunctions",
          "lambda:ListTags",
          "lambda:ListVersionsByFunction",
          "lambda:PublishVersion",
          "lambda:RemovePermission",
          "lambda:TagResource",
          "lambda:UntagResource",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
        ]
        Resource = "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-*"
      },
    ]
  })
}

# Terraform remote state backend (S3 + DynamoDB lock)
resource "aws_iam_role_policy" "github_actions_terraform_state" {
  name = "${var.project_name}-github-actions-tf-state"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TerraformStateObject"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
        ]
        Resource = "arn:aws:s3:::catch-data-tf-state/catch-data/terraform.tfstate"
      },
      {
        Sid      = "TerraformStateBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:GetBucketVersioning"]
        Resource = "arn:aws:s3:::catch-data-tf-state"
      },
      {
        Sid    = "TerraformLockTable"
        Effect = "Allow"
        Action = [
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
        ]
        Resource = "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/catch-data-tf-lock"
      },
      {
        # Required by the configure-aws-credentials action to verify identity.
        Sid      = "STSIdentity"
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity"]
        Resource = "*"
      },
    ]
  })
}

# Infrastructure management — all AWS API calls needed for terraform plan/apply
# on the resources defined in this configuration (S3, SQS, CloudFront, IAM,
# Lambda permissions, CloudWatch Logs).
resource "aws_iam_role_policy" "github_actions_infrastructure" {
  name = "${var.project_name}-github-actions-infra"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3DataBucketManage"
        Effect = "Allow"
        Action = [
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:GetAccelerateConfiguration",
          "s3:GetBucketAcl",
          "s3:GetBucketCORS",
          "s3:GetBucketEncryption",
          "s3:GetBucketLifecycleConfiguration",
          "s3:GetBucketLocation",
          "s3:GetBucketLogging",
          "s3:GetBucketNotification",
          "s3:GetBucketObjectLockConfiguration",
          "s3:GetBucketOwnershipControls",
          "s3:GetBucketPolicy",
          "s3:GetBucketPolicyStatus",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketRequestPayment",
          "s3:GetBucketTagging",
          "s3:GetBucketVersioning",
          "s3:GetBucketWebsite",
          "s3:GetEncryptionConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:GetReplicationConfiguration",
          "s3:ListAllMyBuckets",
          "s3:ListBucket",
          "s3:PutBucketCORS",
          "s3:PutBucketEncryption",
          "s3:PutBucketLifecycleConfiguration",
          "s3:PutBucketNotification",
          "s3:PutBucketOwnershipControls",
          "s3:PutBucketPolicy",
          "s3:PutBucketPublicAccessBlock",
          "s3:PutBucketTagging",
          "s3:PutBucketVersioning",
          "s3:DeleteBucketCORS",
          "s3:DeleteBucketPolicy",
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-*",
          "arn:aws:s3:::${var.project_name}-*/*",
        ]
      },
      {
        Sid    = "SQSManage"
        Effect = "Allow"
        Action = [
          "sqs:CreateQueue",
          "sqs:DeleteQueue",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ListQueues",
          "sqs:ListQueueTags",
          "sqs:SetQueueAttributes",
          "sqs:TagQueue",
          "sqs:UntagQueue",
        ]
        Resource = "arn:aws:sqs:*:${data.aws_caller_identity.current.account_id}:${var.project_name}-*"
      },
      {
        # CloudFront resources cannot be scoped to a project ARN prefix in most
        # read/manage actions; distribution ARNs are known only after creation.
        Sid    = "CloudFrontManage"
        Effect = "Allow"
        Action = [
          "cloudfront:CreateCachePolicy",
          "cloudfront:CreateDistribution",
          "cloudfront:CreateInvalidation",
          "cloudfront:CreateOriginAccessControl",
          "cloudfront:CreateResponseHeadersPolicy",
          "cloudfront:DeleteCachePolicy",
          "cloudfront:DeleteDistribution",
          "cloudfront:DeleteOriginAccessControl",
          "cloudfront:DeleteResponseHeadersPolicy",
          "cloudfront:GetCachePolicy",
          "cloudfront:GetCachePolicyConfig",
          "cloudfront:GetDistribution",
          "cloudfront:GetDistributionConfig",
          "cloudfront:GetOriginAccessControl",
          "cloudfront:GetOriginAccessControlConfig",
          "cloudfront:GetResponseHeadersPolicy",
          "cloudfront:GetResponseHeadersPolicyConfig",
          "cloudfront:ListCachePolicies",
          "cloudfront:ListDistributions",
          "cloudfront:ListOriginAccessControls",
          "cloudfront:ListResponseHeadersPolicies",
          "cloudfront:ListTagsForResource",
          "cloudfront:TagResource",
          "cloudfront:UntagResource",
          "cloudfront:UpdateCachePolicy",
          "cloudfront:UpdateDistribution",
          "cloudfront:UpdateOriginAccessControl",
          "cloudfront:UpdateResponseHeadersPolicy",
        ]
        Resource = "*"
      },
      {
        # IAM management is scoped to project-prefixed roles/users and the
        # GitHub OIDC provider to prevent privilege escalation outside the
        # project's own resources.
        Sid    = "IAMPipelineManage"
        Effect = "Allow"
        Action = [
          "iam:AttachRolePolicy",
          "iam:CreateOpenIDConnectProvider",
          "iam:CreateRole",
          "iam:CreateUser",
          "iam:DeleteOpenIDConnectProvider",
          "iam:DeleteRole",
          "iam:DeleteRolePolicy",
          "iam:DeleteUser",
          "iam:DeleteUserPolicy",
          "iam:DetachRolePolicy",
          "iam:GetOpenIDConnectProvider",
          "iam:GetRole",
          "iam:GetRolePolicy",
          "iam:GetUser",
          "iam:GetUserPolicy",
          "iam:ListAttachedRolePolicies",
          "iam:ListOpenIDConnectProviders",
          "iam:ListRolePolicies",
          "iam:ListRoleTags",
          "iam:ListUserPolicies",
          "iam:ListUserTags",
          "iam:PassRole",
          "iam:PutRolePolicy",
          "iam:PutUserPolicy",
          "iam:TagOpenIDConnectProvider",
          "iam:TagRole",
          "iam:TagUser",
          "iam:UntagOpenIDConnectProvider",
          "iam:UntagRole",
          "iam:UntagUser",
          "iam:UpdateOpenIDConnectProvider",
          "iam:UpdateRole",
        ]
        Resource = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-*",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:user/${var.project_name}-*",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com",
        ]
      },
      {
        Sid    = "CloudWatchLogsManage"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:DeleteRetentionPolicy",
          "logs:DescribeLogGroups",
          "logs:ListTagsForResource",
          "logs:ListTagsLogGroup",
          "logs:PutRetentionPolicy",
          "logs:TagLogGroup",
          "logs:TagResource",
          "logs:UntagLogGroup",
          "logs:UntagResource",
        ]
        Resource = "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-*"
      },
    ]
  })
}
