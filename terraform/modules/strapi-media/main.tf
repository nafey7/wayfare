# Strapi Media Module
# S3 bucket for uploads + CloudFront distribution with OAC

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

# S3 Bucket for Strapi media uploads
resource "aws_s3_bucket" "strapi_media" {
  bucket = "myvoya-${var.environment}-strapi-media"

  tags = merge(
    var.tags,
    {
      Name = "myvoya-${var.environment}-strapi-media"
    }
  )
}

resource "aws_s3_bucket_ownership_controls" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "strapi_media" {
  name                              = "${var.environment}-strapi-media-oac"
  description                       = "OAC for Strapi media S3 bucket in ${var.environment}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "strapi_media" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "Strapi media CDN for ${var.environment}"
  default_root_object = ""
  price_class         = "PriceClass_100" # US, Canada, Europe

  aliases = [var.media_domain_name]

  origin {
    domain_name              = aws_s3_bucket.strapi_media.bucket_regional_domain_name
    origin_id                = "s3-strapi-media"
    origin_access_control_id = aws_cloudfront_origin_access_control.strapi_media.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-strapi-media"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    # Use managed CachingOptimized policy
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-media-cdn"
    }
  )
}

# S3 Bucket Policy - Allow CloudFront OAC to read objects
resource "aws_s3_bucket_policy" "strapi_media" {
  bucket = aws_s3_bucket.strapi_media.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowCloudFrontServicePrincipal"
      Effect    = "Allow"
      Principal = {
        Service = "cloudfront.amazonaws.com"
      }
      Action   = "s3:GetObject"
      Resource = "${aws_s3_bucket.strapi_media.arn}/*"
      Condition = {
        StringEquals = {
          "AWS:SourceArn" = aws_cloudfront_distribution.strapi_media.arn
        }
      }
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.strapi_media]
}
