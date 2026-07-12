# Strapi Media Module Variables

variable "environment" {
  description = "Environment name (e.g., staging, production)"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ARN of the ACM certificate for CloudFront (must be in us-east-1)"
  type        = string
}

variable "media_domain_name" {
  description = "Domain name for the media CDN (e.g., strapi-media.myvoya.ai)"
  type        = string
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS on the S3 bucket"
  type        = list(string)
  default     = ["https://cms.myvoya.ai", "https://cms-staging.myvoya.ai"]
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
