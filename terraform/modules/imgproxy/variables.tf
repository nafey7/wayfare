# imgproxy Module Variables

variable "container_image" {
  description = "Container image for imgproxy (use ECR to avoid Docker Hub rate limits)"
  type        = string
  default     = "darthsim/imgproxy:latest"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs (if assign_public_ip is true)"
  type        = list(string)
  default     = []
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
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
  description = "Security group ID for imgproxy tasks"
  type        = string
}

variable "alb_https_listener_arn" {
  description = "ARN of ALB HTTPS listener for routing rules"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of ALB listener (for depends_on)"
  type        = string
}

# Task configuration
variable "task_cpu" {
  description = "CPU units for task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Memory for task in MB"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

# imgproxy configuration
variable "imgproxy_key" {
  description = "imgproxy signing key (hex-encoded, 32 bytes)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "imgproxy_salt" {
  description = "imgproxy signing salt (hex-encoded, 32 bytes)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "allow_insecure_urls" {
  description = "Allow unsigned URLs (set to false in production)"
  type        = bool
  default     = false
}

variable "allowed_sources" {
  description = "Comma-separated list of allowed source domains"
  type        = string
  default     = ""
}

variable "concurrency" {
  description = "Maximum number of simultaneous image requests"
  type        = number
  default     = 10
}

variable "max_src_resolution" {
  description = "Maximum source image resolution in megapixels"
  type        = number
  default     = 50
}

# Networking
variable "assign_public_ip" {
  description = "Assign public IP to tasks (for public subnets)"
  type        = bool
  default     = false
}

variable "enable_ecs_exec" {
  description = "Enable ECS Exec for debugging"
  type        = bool
  default     = false
}

variable "enable_health_checks" {
  description = "Enable health checks on target group"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# S3 source support (private buckets like user profile photos)
variable "enable_s3_sources" {
  description = "Enable imgproxy IMGPROXY_USE_S3 so it can fetch s3:// sources via IAM."
  type        = bool
  default     = false
}

variable "s3_region" {
  description = "Region for s3:// sources (matches the photos bucket region)."
  type        = string
  default     = "us-east-1"
}

# ECS Cluster name (for autoscaling resource_id)
variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

# Autoscaling Configuration
variable "enable_autoscaling" {
  description = "Enable autoscaling for imgproxy service"
  type        = bool
  default     = true
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 1
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 4
}

variable "autoscaling_cpu_target" {
  description = "Target CPU utilization percentage for autoscaling"
  type        = number
  default     = 60  # Scale up before hitting 70% spike threshold
}

variable "autoscaling_memory_target" {
  description = "Target memory utilization percentage for autoscaling"
  type        = number
  default     = 70
}
