# Production Environment Variables

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
  default     = "10.1.0.0/16"  # Different from staging (10.0.0.0/16)
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
  default     = 10  # Keep more images in prod for rollback
}

# Logs
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90  # Longer retention in prod
}

# ALB
variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS (wildcard *.myvoya.ai)"
  type        = string
  default     = "arn:aws:acm:us-east-1:155304839180:certificate/358296c6-21e2-407c-a506-ef3d74b2e301"
}

# ECS
variable "container_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "2026.3.1.p1"  # Use specific version in prod
}

variable "ecs_task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 2048  # 2 vCPU for production
}

variable "ecs_task_memory" {
  description = "Memory for ECS task in MB"
  type        = number
  default     = 4096  # 4GB for production
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "enable_autoscaling" {
  description = "Enable auto-scaling for ECS service"
  type        = bool
  default     = true
}

variable "autoscaling_min_capacity" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 2
}

variable "autoscaling_max_capacity" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 8  # Higher max for production
}

variable "enable_ecs_exec" {
  description = "Enable ECS Exec for debugging"
  type        = bool
  default     = false  # Disable by default in prod
}

variable "enable_ssm_session_manager" {
  description = "Enable SSM Session Manager for debugging"
  type        = bool
  default     = false
}

# Application URLs
variable "frontend_url" {
  description = "Frontend URL for CORS configuration"
  type        = string
  default     = "https://www.myvoya.ai"
}

variable "backend_url" {
  description = "Backend URL"
  type        = string
  default     = "https://www.myvoya.ai"
}

variable "admin_emails" {
  description = "Comma-separated list of admin emails"
  type        = string
  default     = "admin@myvoya.ai"
}

variable "sendgrid_from_email" {
  description = "SendGrid from email address"
  type        = string
  default     = "no-reply@myvoya.ai"
}

# FlightLogic IP Spoofing Workaround
variable "flightlogic_spoof_ip" {
  description = "IP to use in X-Forwarded-For header until new NAT Gateway IP is whitelisted"
  type        = string
  default     = "44.208.39.138"  # Existing prod NAT Gateway IP
}

# FlightLogic Stripe Account ID
variable "flightlogic_stripe_account_id" {
  description = "FlightLogic Stripe Connect account ID for payment processing"
  type        = string
  default     = "acct_1SYDWlPFaJGxewbo"
}

# imgproxy
variable "imgproxy_enabled" {
  description = "Enable imgproxy URL signing for backend image URL transformation"
  type        = bool
  default     = true
}

variable "imgproxy_task_cpu" {
  description = "CPU units for imgproxy task (256 = 0.25 vCPU)"
  type        = number
  default     = 256
}

variable "imgproxy_task_memory" {
  description = "Memory for imgproxy task in MB"
  type        = number
  default     = 512
}

variable "imgproxy_desired_count" {
  description = "Desired number of imgproxy tasks"
  type        = number
  default     = 2  # Higher for prod reliability
}

# imgproxy Security Keys (must match backend secrets)
# These should be provided via terraform.tfvars (not committed)
variable "imgproxy_key" {
  description = "imgproxy signing key (hex)"
  type        = string
  sensitive   = true
}

variable "imgproxy_salt" {
  description = "imgproxy signing salt (hex)"
  type        = string
  sensitive   = true
}

# Tags
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "Voya"
    Environment = "production"
    ManagedBy   = "Terraform"
    Repository  = "voya"
  }
}
