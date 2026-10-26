
output "frontend_bucket_name" {
  description = "Name of the private S3 bucket"
  value       = aws_s3_bucket.frontend.bucket
}

output "listings_table_name" {
  description = "DynamoDB table for housing listings"
  value       = aws_dynamodb_table.listings.name
}

output "aws_region" {
  description = "AWS deployment region"
  value       = var.aws_region
}

output "environment" {
  description = "Deployment environment"
  value       = var.environment
}
