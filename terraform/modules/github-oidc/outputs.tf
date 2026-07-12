# GitHub OIDC Module Outputs

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions IAM role"
  value       = aws_iam_role.github_actions.arn
}

output "oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = aws_iam_openid_connect_provider.github.arn
}

output "github_actions_terraform_role_arn" {
  description = "ARN of the GitHub Actions Terraform IAM role"
  value       = aws_iam_role.github_actions_terraform.arn
}
