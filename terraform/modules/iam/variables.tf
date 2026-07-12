# IAM Module Variables

variable "environment" {
  description = "Environment name (e.g., staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "enable_ssm_session_manager" {
  description = "Enable SSM Session Manager for debugging ECS tasks"
  type        = bool
  default     = false
}

variable "enable_strapi_s3" {
  description = "Enable S3 access for Strapi media uploads"
  type        = bool
  default     = false
}

variable "enable_strapi_secrets" {
  description = "Enable Strapi secrets access for ECS execution role"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
