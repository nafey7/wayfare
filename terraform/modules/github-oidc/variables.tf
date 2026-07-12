# GitHub OIDC Module Variables

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "ecs_task_execution_role_arns" {
  description = "List of ECS task execution role ARNs (all environments)"
  type        = list(string)
}

variable "ecs_task_role_arns" {
  description = "List of ECS task role ARNs (all environments)"
  type        = list(string)
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
