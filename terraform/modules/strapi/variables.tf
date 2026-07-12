# Strapi ECS Module Variables

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster (for autoscaling resource_id)"
  type        = string
}

variable "task_execution_role_arn" {
  description = "ARN of ECS task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of ECS task role"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID for Strapi tasks"
  type        = string
}

variable "alb_https_listener_arn" {
  description = "ARN of ALB HTTPS listener for host-based routing rule"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of ALB listener (for depends_on)"
  type        = string
}

# Container
variable "container_image" {
  description = "Container image for Strapi (ECR URL)"
  type        = string
}

variable "task_cpu" {
  description = "CPU units for task (512 = 0.5 vCPU)"
  type        = number
  default     = 512
}

variable "task_memory" {
  description = "Memory for task in MB"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

# Strapi configuration
variable "cms_domain" {
  description = "Domain name for host-based ALB routing (e.g., cms.myvoya.ai)"
  type        = string
}

variable "app_url" {
  description = "Full URL for Strapi (e.g., https://cms.myvoya.ai)"
  type        = string
}

# Database
variable "db_address" {
  description = "RDS hostname"
  type        = string
}

variable "db_port" {
  description = "RDS port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "strapi"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "strapi_admin"
}

variable "db_master_user_secret_arn" {
  description = "ARN of the RDS-managed master user secret (for DATABASE_PASSWORD)"
  type        = string
  default     = ""
}

# S3 / Media
variable "s3_bucket_name" {
  description = "S3 bucket name for media uploads"
  type        = string
}

variable "cdn_url" {
  description = "CDN URL for media (e.g., https://strapi-media.myvoya.ai)"
  type        = string
}

# Email
variable "sendgrid_from_email" {
  description = "Default from email for SendGrid"
  type        = string
  default     = "noreply@myvoya.ai"
}

variable "sendgrid_api_key_arn" {
  description = "ARN of the SendGrid API key secret in Secrets Manager"
  type        = string
  default     = ""
}

# Secrets
variable "secret_arns" {
  description = "Map of secret name to ARN for Strapi secrets"
  type        = map(string)
}

# Autoscaling
variable "enable_autoscaling" {
  description = "Enable autoscaling for Strapi service"
  type        = bool
  default     = false
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 3
}

# Debugging
variable "enable_ecs_exec" {
  description = "Enable ECS Exec for debugging"
  type        = bool
  default     = false
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
