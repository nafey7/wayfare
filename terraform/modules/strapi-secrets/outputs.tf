# Strapi Secrets Module Outputs

output "secret_arns" {
  description = "ARNs of all Strapi secrets"
  value       = { for k, v in aws_secretsmanager_secret.strapi : k => v.arn }
}

output "secret_names" {
  description = "Names of all Strapi secrets"
  value       = { for k, v in aws_secretsmanager_secret.strapi : k => v.name }
}
