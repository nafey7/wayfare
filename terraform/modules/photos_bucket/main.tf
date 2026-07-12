# Photos Bucket Module
# Private S3 bucket for user-uploaded profile photos.
# Originals are served on the fly via imgproxy (s3:// source) and cached
# at CloudFlare (cdn.myvoya.ai). Backend writes/deletes; imgproxy reads.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

resource "aws_s3_bucket" "photos" {
  bucket = "myvoya-${var.environment}-photos"

  tags = merge(
    var.tags,
    {
      Name = "myvoya-${var.environment}-photos"
    }
  )
}

resource "aws_s3_bucket_ownership_controls" "photos" {
  bucket = aws_s3_bucket.photos.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Avatars are disposable; UUID-in-key handles cache busting on replace.
resource "aws_s3_bucket_versioning" "photos" {
  bucket = aws_s3_bucket.photos.id

  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "photos" {
  bucket = aws_s3_bucket.photos.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "photos" {
  bucket = aws_s3_bucket.photos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "photos" {
  bucket = aws_s3_bucket.photos.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET", "DELETE", "HEAD"]
    allowed_origins = var.cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}

# Safety net for orphans (failed replace flows). Backend deletes synchronously;
# this is the backstop.
resource "aws_s3_bucket_lifecycle_configuration" "photos" {
  bucket = aws_s3_bucket.photos.id

  rule {
    id     = "expire-incomplete-uploads"
    status = "Enabled"

    filter {
      prefix = "incomplete/"
    }

    expiration {
      days = 1
    }
  }

  rule {
    id     = "abort-multipart"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Least-privilege policy on the shared backend + imgproxy task role.
# Backend: PutObject (upload) + DeleteObject (replace / user delete).
# imgproxy: GetObject (read for resize). Single policy covers both since this
# stack uses the same task role for both services.
#
# `s3:GetObject` covers both GET and HEAD requests at the IAM level; there is
# no separate `s3:HeadObject` action. `s3:ListBucket` is intentionally omitted —
# neither service enumerates keys.
resource "aws_iam_role_policy" "photos_access" {
  name = "${var.environment}-ecs-photos-access"
  role = var.backend_task_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "BackendWrite"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.photos.arn}/*"
      },
      {
        Sid      = "ImgproxyRead"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.photos.arn}/*"
      }
    ]
  })
}

# Separate role attachment only used if imgproxy runs under a distinct role.
resource "aws_iam_role_policy" "imgproxy_photos_r" {
  count = var.imgproxy_task_role_name != "" && var.imgproxy_task_role_name != var.backend_task_role_name ? 1 : 0

  name = "${var.environment}-imgproxy-photos-r"
  role = var.imgproxy_task_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.photos.arn}/*"
      }
    ]
  })
}

# Publish bucket name to SSM for app config / debugging.
resource "aws_ssm_parameter" "photos_bucket_name" {
  name  = "/voya/${var.environment}/s3_photos_bucket"
  type  = "String"
  value = aws_s3_bucket.photos.bucket

  tags = var.tags
}
