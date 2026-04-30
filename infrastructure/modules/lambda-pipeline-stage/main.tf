locals {
  name_with_environment = "${var.name}-${var.environment}"
  read_object_arns = [
    for prefix in var.read_prefixes :
    "${var.s3_bucket_arn}/${trim(prefix, "/")}/*"
  ]
  write_object_arns = [
    for prefix in var.write_prefixes :
    "${var.s3_bucket_arn}/${trim(prefix, "/")}/*"
  ]
  # Combined list of prefixes for s3:ListBucket condition (deduplicated)
  list_prefix_conditions = distinct([
    for prefix in concat(var.read_prefixes, var.write_prefixes) :
    "${trim(prefix, "/")}/*"
  ])

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_ecr_repository" "this" {
  name                 = local.name_with_environment
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only the last 10 untagged images"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = var.untagged_image_retention_count
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_iam_role" "this" {
  name = "${var.name}-lambda-${var.environment}"

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

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.this.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "s3_access" {
  name = "${var.name}-s3-${var.environment}"
  role = aws_iam_role.this.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = local.read_object_arns
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = local.write_object_arns
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = var.s3_bucket_arn
        Condition = {
          StringLike = {
            "s3:prefix" = local.list_prefix_conditions
          }
        }
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${local.name_with_environment}"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_lambda_function" "this" {
  function_name = local.name_with_environment
  role          = aws_iam_role.this.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.this.repository_url}:${var.image_tag}"
  timeout       = var.timeout
  memory_size   = var.memory_size

  environment {
    variables = merge(
      var.environment_variables,
      {
        ENVIRONMENT    = var.environment
        S3_BUCKET_NAME = var.s3_bucket_name
        LOG_FORMAT     = "json"
      }
    )
  }

  depends_on = [aws_cloudwatch_log_group.this]

  tags = local.common_tags
}
