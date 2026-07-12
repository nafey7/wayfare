# FlightLogic Inspector Module
# Deploys nginx as a reverse proxy to inspect FlightLogic API requests/responses

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "inspector" {
  name              = "/ecs/${var.environment}-flightlogic-inspector"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-flightlogic-inspector-logs"
    }
  )
}

# ECS Task Definition
resource "aws_ecs_task_definition" "inspector" {
  family                   = "${var.environment}-flightlogic-inspector"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "flightlogic-inspector"
      image = "155304839180.dkr.ecr.us-east-1.amazonaws.com/flightlogic-nginx-proxy:latest"

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.inspector.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "inspector"
        }
      }
    }
  ])

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-flightlogic-inspector-task"
    }
  )
}

# ECS Service
resource "aws_ecs_service" "inspector" {
  name                   = "${var.environment}-flightlogic-inspector"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.inspector.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = var.enable_ecs_exec

  network_configuration {
    subnets          = var.assign_public_ip ? var.public_subnet_ids : var.private_subnet_ids
    security_groups  = [var.inspector_security_group_id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.inspector_proxy.arn
    container_name   = "flightlogic-inspector"
    container_port   = 8080  # Proxy port
  }

  depends_on = [var.alb_listener_arn]

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-flightlogic-inspector-service"
    }
  )
}

# NOTE: Web UI target group commented out - nginx proxy doesn't have a web UI
# resource "aws_lb_target_group" "inspector" {
#   name        = "${var.environment}-fl-inspector"
#   port        = 8081
#   protocol    = "HTTP"
#   vpc_id      = var.vpc_id
#   target_type = "ip"
#
#   dynamic "health_check" {
#     for_each = var.enable_health_checks ? [1] : []
#     content {
#       enabled             = true
#       healthy_threshold   = 2
#       unhealthy_threshold = 3
#       timeout             = 10
#       interval            = 30
#       path                = "/"
#       matcher             = "200,301,302,307,308,401,403"
#     }
#   }
#
#   deregistration_delay = 30
#
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.environment}-fl-inspector-tg"
#     }
#   )
# }

# Target Group for Inspector Proxy (port 8080)
resource "aws_lb_target_group" "inspector_proxy" {
  name        = "${var.environment}-fl-proxy"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  dynamic "health_check" {
    for_each = var.enable_health_checks ? [1] : []
    content {
      enabled             = true
      healthy_threshold   = 2
      unhealthy_threshold = 10
      timeout             = 30
      interval            = 300
      port                = "traffic-port"
      path                = "/health"
      matcher             = "200"
    }
  }

  deregistration_delay = 30

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-fl-proxy-tg"
    }
  )
}

# NOTE: Web UI listener rule commented out - nginx proxy doesn't have a web UI
# resource "aws_lb_listener_rule" "inspector" {
#   listener_arn = var.alb_https_listener_arn
#
#   action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.inspector.arn
#   }
#
#   condition {
#     path_pattern {
#       values = ["/inspector*"]
#     }
#   }
#
#   priority = 100
#
#   tags = merge(
#     var.tags,
#     {
#       Name = "${var.environment}-inspector-rule"
#     }
#   )
# }

# ALB Listener Rule for Inspector Proxy (path-based routing)
resource "aws_lb_listener_rule" "inspector_proxy" {
  listener_arn = var.alb_https_listener_arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.inspector_proxy.arn
  }

  condition {
    path_pattern {
      values = ["/flightlogic/*"]
    }
  }

  priority = 99

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-inspector-proxy-rule"
    }
  )
}
