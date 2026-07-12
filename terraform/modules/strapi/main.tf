# Strapi ECS Module
# Deploys Strapi CMS as an ECS Fargate service with host-based ALB routing

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "strapi" {
  name              = "/ecs/${var.environment}-strapi"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-logs"
    }
  )
}

# ECS Task Definition
resource "aws_ecs_task_definition" "strapi" {
  family                   = "${var.environment}-strapi"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "strapi"
      image = var.container_image

      portMappings = [
        {
          containerPort = 1337
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "STRAPI_TELEMETRY_DISABLED", value = "true" },
        { name = "HOST", value = "0.0.0.0" },
        { name = "PORT", value = "1337" },
        { name = "APP_URL", value = var.app_url },
        { name = "STRAPI_ADMIN_BACKEND_URL", value = var.app_url },
        { name = "DATABASE_CLIENT", value = "postgres" },
        { name = "DATABASE_HOST", value = var.db_address },
        { name = "DATABASE_PORT", value = tostring(var.db_port) },
        { name = "DATABASE_NAME", value = var.db_name },
        { name = "DATABASE_USERNAME", value = var.db_username },
        { name = "DATABASE_SSL", value = "false" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "AWS_S3_BUCKET", value = var.s3_bucket_name },
        { name = "CDN_URL", value = var.cdn_url },
        { name = "SENDGRID_FROM_EMAIL", value = var.sendgrid_from_email },
      ]

      secrets = concat(
        [
          { name = "APP_KEYS", valueFrom = var.secret_arns["APP_KEYS"] },
          { name = "API_TOKEN_SALT", valueFrom = var.secret_arns["API_TOKEN_SALT"] },
          { name = "ADMIN_JWT_SECRET", valueFrom = var.secret_arns["ADMIN_JWT_SECRET"] },
          { name = "TRANSFER_TOKEN_SALT", valueFrom = var.secret_arns["TRANSFER_TOKEN_SALT"] },
          { name = "JWT_SECRET", valueFrom = var.secret_arns["JWT_SECRET"] },
        ],
        var.sendgrid_api_key_arn != "" ? [
          { name = "SENDGRID_API_KEY", valueFrom = var.sendgrid_api_key_arn }
        ] : [],
        var.db_master_user_secret_arn != "" ? [
          {
            name      = "DATABASE_PASSWORD"
            valueFrom = "${var.db_master_user_secret_arn}:password::"
          }
        ] : []
      )

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.strapi.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "strapi"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:1337/_health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 120
      }
    }
  ])

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-task"
    }
  )
}

# ECS Service
resource "aws_ecs_service" "strapi" {
  name                   = "${var.environment}-strapi"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.strapi.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = var.enable_ecs_exec

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.strapi.arn
    container_name   = "strapi"
    container_port   = 1337
  }

  depends_on = [var.alb_listener_arn]

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-service"
    }
  )
}

# Target Group for Strapi
resource "aws_lb_target_group" "strapi" {
  name        = "${var.environment}-strapi"
  port        = 1337
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    port                = "traffic-port"
    path                = "/_health"
    matcher             = "200,204"
  }

  deregistration_delay = 60

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-tg"
    }
  )
}

# ALB Listener Rule for Strapi (host-based routing)
resource "aws_lb_listener_rule" "strapi" {
  listener_arn = var.alb_https_listener_arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.strapi.arn
  }

  condition {
    host_header {
      values = [var.cms_domain]
    }
  }

  priority = 90

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-rule"
    }
  )
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "strapi" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.autoscaling_max_capacity
  min_capacity       = var.autoscaling_min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.strapi.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "strapi_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-strapi-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.strapi[0].resource_id
  scalable_dimension = aws_appautoscaling_target.strapi[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.strapi[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto Scaling Policy - Memory
resource "aws_appautoscaling_policy" "strapi_memory" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-strapi-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.strapi[0].resource_id
  scalable_dimension = aws_appautoscaling_target.strapi[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.strapi[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
