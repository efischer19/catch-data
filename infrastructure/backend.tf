# Remote state backend configuration for {{PROJECT_NAME}}
# See ADR-016 (Terraform for IaC)
#
# Prerequisites — create these resources manually or with a bootstrap script
# BEFORE running `terraform init`:
#   1. S3 bucket for state storage ({{TF_STATE_BUCKET}})
#   2. DynamoDB table for state locking ({{TF_LOCK_TABLE}})
#
# Replace all {{...}} placeholders with your real values.

terraform {
  backend "s3" {
    bucket         = "{{TF_STATE_BUCKET}}"
    key            = "{{PROJECT_NAME}}/terraform.tfstate"
    region         = "{{AWS_REGION}}"
    dynamodb_table = "{{TF_LOCK_TABLE}}"
    encrypt        = true
  }
}
