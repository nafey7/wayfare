# Test Environment Variables

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use (optional, uses default AWS credential chain if not set)"
  type        = string
  default     = null
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.1.0.0/16"  # Different CIDR from staging (10.0.0.0/16)
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "mongodb_cidr" {
  description = "CIDR block for MongoDB Atlas VPC peering"
  type        = string
  default     = "192.168.248.0/21"
}

# ECR
variable "ecr_image_retention_count" {
  description = "Number of images to retain in ECR"
  type        = number
  default     = 5
}

# Logs
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

# ALB
variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS (leave empty for HTTP-only)"
  type        = string
  default     = "arn:aws:acm:us-east-1:155304839180:certificate/34caadb6-f8d2-4ae9-857c-365c9e6f8e96"
}

# ECS
variable "container_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MB"
  type        = number
  default     = 2048
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "enable_autoscaling" {
  description = "Enable auto-scaling for ECS service"
  type        = bool
  default     = false
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 3
}

variable "enable_ecs_exec" {
  description = "Enable ECS Exec for debugging"
  type        = bool
  default     = false
}

variable "enable_ssm_session_manager" {
  description = "Enable SSM Session Manager for debugging"
  type        = bool
  default     = false
}

# Application
variable "frontend_url" {
  description = "Frontend URL for CORS configuration"
  type        = string
  default     = "https://test.myvoya.ai"
}

variable "admin_emails" {
  description = "Comma-separated list of admin emails"
  type        = string
  default     = "admin@myvoya.ai,dev@myvoya.ai"
}

variable "sendgrid_from_email" {
  description = "SendGrid from email address"
  type        = string
  default     = "no-reply@myvoya.ai"
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Voya"
    Environment = "test"
    ManagedBy   = "Terraform"
    Repository  = "voya"
  }
}
