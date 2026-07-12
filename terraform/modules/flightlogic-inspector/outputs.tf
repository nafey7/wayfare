output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.inspector.name
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.inspector.arn
}

output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.inspector.name
}

# NOTE: Commented out - nginx proxy doesn't have web UI target group
# output "target_group_arn" {
#   description = "ARN of the target group"
#   value       = aws_lb_target_group.inspector.arn
# }

output "proxy_target_group_arn" {
  description = "ARN of the proxy target group (port 8080)"
  value       = aws_lb_target_group.inspector_proxy.arn
}

# NOTE: Commented out - nginx proxy doesn't have a web UI
# output "inspector_url" {
#   description = "URL of the FlightLogic inspector web UI"
#   value       = "https://inspector.${var.domain_name}"
# }

output "proxy_url" {
  description = "URL to use as FLIGHTLOGIC_API_URL for proxying requests (via ALB)"
  value       = "https://${var.domain_name}/flightlogic"
}
