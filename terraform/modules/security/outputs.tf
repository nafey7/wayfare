# Security Module Outputs

output "alb_security_group_id" {
  description = "ID of the ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID of the ECS task security group"
  value       = aws_security_group.ecs.id
}

output "ssm_endpoint_security_group_id" {
  description = "ID of the SSM VPC endpoint security group"
  value       = var.enable_vpc_endpoints ? aws_security_group.ssm_endpoint[0].id : null
}

output "secrets_endpoint_security_group_id" {
  description = "ID of the Secrets Manager VPC endpoint security group"
  value       = var.enable_vpc_endpoints ? aws_security_group.secrets_endpoint[0].id : null
}

output "ecr_endpoint_security_group_id" {
  description = "ID of the ECR VPC endpoint security group"
  value       = var.enable_vpc_endpoints ? aws_security_group.ecr_endpoint[0].id : null
}

output "strapi_rds_security_group_id" {
  description = "ID of the Strapi RDS security group"
  value       = var.enable_strapi_rds ? aws_security_group.strapi_rds[0].id : null
}
