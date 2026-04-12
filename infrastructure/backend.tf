# Remote state backend configuration for catch-data
# See ADR-016 (Terraform for IaC)
#
# Prerequisites — create these resources manually or with a bootstrap script
# BEFORE running `terraform init`:
#   1. S3 bucket for state storage (catch-data-tf-state)
#   2. DynamoDB table for state locking (catch-data-tf-lock)

terraform {
  backend "s3" {
    bucket         = "catch-data-tf-state"
    key            = "catch-data/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "catch-data-tf-lock"
    encrypt        = true
  }
}
