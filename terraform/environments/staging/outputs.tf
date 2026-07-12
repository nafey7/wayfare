# Staging Environment Outputs

# Networking Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "nat_gateway_public_ip" {
  description = "Public IP of NAT Gateway (whitelist for external APIs)"
  value       = module.networking.nat_gateway_public_ip
}

# ALB Outputs
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.alb_dns_name
}

output "alb_url" {
  description = "Full URL to access the application"
  value       = var.acm_certificate_arn != "" ? "https://${module.alb.alb_dns_name}" : "http://${module.alb.alb_dns_name}"
}

# ECR Outputs
output "ecr_repository_url" {
  description = "URL of ECR repository for pushing images"
  value       = module.ecr.repository_url
}

# ECS Outputs
output "ecs_cluster_name" {
  description = "Name of ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of ECS service"
  value       = module.ecs.service_name
}

output "ecs_task_definition_family" {
  description = "Family of ECS task definition"
  value       = module.ecs.task_definition_family
}

# Secrets Outputs
output "secrets_to_populate" {
  description = "List of secrets that need values set manually"
  value       = keys(module.secrets.secret_arns)
}

# CloudWatch Logs
output "log_group_name" {
  description = "Name of CloudWatch log group"
  value       = module.ecs.log_group_name
}

# imgproxy Outputs
output "imgproxy_service_name" {
  description = "Name of imgproxy ECS service"
  value       = module.imgproxy.service_name
}

output "imgproxy_url" {
  description = "URL path for imgproxy (via CDN subdomain)"
  value       = "https://cdn-staging.myvoya.ai${module.imgproxy.imgproxy_url_path}"
}

# GitHub Actions
output "github_actions_role_arn" {
  description = "ARN of GitHub Actions IAM role for CI/CD"
  value       = module.github_oidc.github_actions_role_arn
}

# Deployment Instructions
output "deployment_instructions" {
  description = "Next steps after infrastructure deployment"
  value = <<-EOT

    ========================================
    STAGING ENVIRONMENT DEPLOYED
    ========================================

    Application URL: ${var.acm_certificate_arn != "" ? "https://${module.alb.alb_dns_name}" : "http://${module.alb.alb_dns_name}"}

    NEXT STEPS:

    1. SET SECRET VALUES (REQUIRED):
       ${join("\n       ", [for k, v in module.secrets.secret_arns : "aws secretsmanager put-secret-value --secret-id ${v} --secret-string 'YOUR_VALUE' --profile voya-poweruser"])}

    2. BUILD & PUSH DOCKER IMAGE:
       docker build -t ${module.ecr.repository_url}:latest .
       aws ecr get-login-password --region us-east-1 --profile voya-poweruser | docker login --username AWS --password-stdin ${module.ecr.repository_url}
       docker push ${module.ecr.repository_url}:latest

    3. FORCE NEW DEPLOYMENT:
       aws ecs update-service --cluster ${module.ecs.cluster_name} --service ${module.ecs.service_name} --force-new-deployment --profile voya-poweruser

    4. MONITOR DEPLOYMENT:
       aws ecs describe-services --cluster ${module.ecs.cluster_name} --services ${module.ecs.service_name} --profile voya-poweruser
       aws logs tail /ecs/staging-voya-backend --follow --profile voya-poweruser

    5. (OPTIONAL) CONFIGURE DNS:
       Create CNAME record: staging.myvoya.ai -> ${module.alb.alb_dns_name}

    NAT Gateway IP (whitelist for external APIs): ${module.networking.nat_gateway_public_ip}

    ========================================
  EOT
}
