# Strapi RDS Module Outputs

output "db_endpoint" {
  description = "RDS endpoint (hostname:port)"
  value       = aws_db_instance.strapi.endpoint
}

output "db_address" {
  description = "RDS hostname"
  value       = aws_db_instance.strapi.address
}

output "db_port" {
  description = "RDS port"
  value       = aws_db_instance.strapi.port
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.strapi.db_name
}

output "db_username" {
  description = "Master username"
  value       = aws_db_instance.strapi.username
}

output "db_instance_id" {
  description = "RDS instance identifier"
  value       = aws_db_instance.strapi.id
}

output "db_master_user_secret_arn" {
  description = "ARN of the RDS-managed master user secret in Secrets Manager"
  value       = aws_db_instance.strapi.master_user_secret[0].secret_arn
}
