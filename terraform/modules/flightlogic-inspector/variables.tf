variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "inspector_security_group_id" {
  description = "Security group ID for inspector service"
  type        = string
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "task_execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "alb_listener_arn" {
  description = "ALB HTTP listener ARN"
  type        = string
}

variable "alb_https_listener_arn" {
  description = "ALB HTTPS listener ARN"
  type        = string
}

variable "domain_name" {
  description = "Domain name for inspector subdomain (e.g., staging.myvoya.ai)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "task_cpu" {
  description = "CPU units for inspector task (256, 512, 1024, etc.)"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Memory for inspector task in MB (512, 1024, 2048, etc.)"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of inspector tasks"
  type        = number
  default     = 1
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "enable_ecs_exec" {
  description = "Enable ECS Exec (SSH-like access) for debugging"
  type        = bool
  default     = false
}

variable "assign_public_ip" {
  description = "Assign public IP to ECS tasks for direct access (bypassing ALB)"
  type        = bool
  default     = false
}

variable "enable_health_checks" {
  description = "Enable health checks (disable for initial debugging)"
  type        = bool
  default     = true
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ECS tasks (when assign_public_ip is true)"
  type        = list(string)
  default     = []
}
