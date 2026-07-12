output "bucket_name" {
  description = "Name of the photos bucket."
  value       = aws_s3_bucket.photos.bucket
}

output "bucket_arn" {
  description = "ARN of the photos bucket."
  value       = aws_s3_bucket.photos.arn
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the photos bucket (for imgproxy / s3:// sources)."
  value       = aws_s3_bucket.photos.bucket_regional_domain_name
}
