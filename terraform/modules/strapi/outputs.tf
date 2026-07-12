# Strapi ECS Module Outputs

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.strapi.name
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.strapi.arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.strapi.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.strapi.name
}
