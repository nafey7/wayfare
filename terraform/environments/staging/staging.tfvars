# Staging Environment Configuration
# This file is committed to git and shared across the team
# For local overrides (like aws_profile), use terraform.tfvars (gitignored)

aws_region = "us-east-1"

# Networking
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]
mongodb_cidr       = "192.168.248.0/21"

# ECR
ecr_image_retention_count = 5

# CloudWatch Logs
log_retention_days = 30

# ALB & SSL
acm_certificate_arn = "arn:aws:acm:us-east-1:155304839180:certificate/c663d9d0-9a0f-4403-b338-aedd8c473298"

# ECS Task Configuration
container_image_tag = "latest"
ecs_task_cpu        = 1024  # 1 vCPU
ecs_task_memory     = 2048  # 2 GB
ecs_desired_count   = 1

# Auto-scaling (disabled by default for cost savings in staging)
enable_autoscaling       = false
autoscaling_min_capacity = 1
autoscaling_max_capacity = 3

# Debugging (disabled in staging for security)
enable_ecs_exec            = false
enable_ssm_session_manager = false

# Application Configuration
frontend_url        = "https://staging.myvoya.ai"
admin_emails        = "admin@myvoya.ai,dev@myvoya.ai"
sendgrid_from_email = "no-reply@myvoya.ai"

# Tags
common_tags = {
  Project     = "Voya"
  Environment = "staging"
  ManagedBy   = "Terraform"
  Repository  = "voya"
  Owner       = "DevOps"
}
