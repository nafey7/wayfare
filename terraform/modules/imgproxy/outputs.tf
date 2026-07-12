# imgproxy Module Outputs

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.imgproxy.name
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.imgproxy.arn
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.imgproxy.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.imgproxy.name
}

output "imgproxy_url_path" {
  description = "URL path for imgproxy (append to ALB domain)"
  value       = "/imgproxy"
}
