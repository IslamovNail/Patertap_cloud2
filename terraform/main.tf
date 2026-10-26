
terraform {
  required_version = ">= 1.5.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  project_name = "patertap"
  common_tags = {
    Project     = "PaterTap"
    Environment = var.environment
  }
}

# Private S3 bucket
resource "aws_s3_bucket" "frontend" {
  bucket_prefix = "${local.project_name}-frontend-"
  force_destroy = false
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Database for housing listings
resource "aws_dynamodb_table" "listings" {
  name         = "${local.project_name}-listings-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "listing_id"

  attribute {
    name = "listing_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = local.common_tags
}

# IAM role for the future Lambda function
resource "aws_iam_role" "app_lambda" {
  name = "${local.project_name}-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = local.common_tags
}

# Permit Lambda to write logs
resource "aws_iam_role_policy" "lambda_logs" {
  name = "${local.project_name}-lambda-logs"
  role = aws_iam_role.app_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "${aws_cloudwatch_log_group.app.arn}:*"
    }]
  })
}

# Permit access only to the listings table
resource "aws_iam_role_policy" "lambda_listings" {
  name = "${local.project_name}-lambda-listings"
  role = aws_iam_role.app_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ]
      Resource = aws_dynamodb_table.listings.arn
    }]
  })
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/lambda/${local.project_name}-${var.environment}"
  retention_in_days = 7
  tags              = local.common_tags
}
