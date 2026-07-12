# Secrets Module Outputs

output "secret_arns" {
  description = "ARNs of all secrets"
  value       = { for k, v in aws_secretsmanager_secret.app : k => v.arn }
}

output "secret_names" {
  description = "Names of all secrets"
  value       = { for k, v in aws_secretsmanager_secret.app : k => v.name }
}

output "mongodb_uri_arn" {
  description = "ARN of MongoDB URI secret"
  value       = aws_secretsmanager_secret.app["MONGODB_URI"].arn
}

output "jwt_secret_arn" {
  description = "ARN of JWT secret"
  value       = aws_secretsmanager_secret.app["JWT_SECRET"].arn
}

output "gemini_api_key_arn" {
  description = "ARN of Gemini API key secret"
  value       = aws_secretsmanager_secret.app["GEMINI_API_KEY"].arn
}
