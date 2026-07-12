# ECS Module
# Creates ECS cluster, task definition, and service

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

# CloudWatch Log Groups
# Main backend log group (used by ECS awslogs driver)
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.environment}-voya-backend"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ecs-logs"
    }
  )
}

# Topic-based log groups for application logging
locals {
  log_topics = ["agents", "auth", "database", "errors", "flights", "hotels"]
}

resource "aws_cloudwatch_log_group" "topics" {
  for_each          = toset(local.log_topics)
  name              = "/ecs/${var.environment}-voya-${each.key}"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-voya-${each.key}-logs"
    }
  )
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-cluster"
    }
  )
}

# Look up the currently deployed task definition to preserve the image tag set by CI/CD.
# This prevents terraform apply from reverting the image to a stale default.
data "aws_ecs_task_definition" "current" {
  task_definition = "${var.environment}-fastapi-react"
}

locals {
  # Preserve the CI/CD-deployed image tag unless explicitly overridden
  current_image = try(
    jsondecode(data.aws_ecs_task_definition.current.container_definitions)[0].image,
    "${var.ecr_repository_url}:${var.container_image_tag}"
  )
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "${var.environment}-fastapi-react"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name  = "fastapi-react-container"
    image = local.current_image

    portMappings = [{
      containerPort = 80
      protocol      = "tcp"
    }]

    environment = concat([
      {
        name  = "ENVIRONMENT"
        value = var.environment
      },
      {
        name  = "DEBUG"
        value = tostring(var.debug_mode)
      },
      {
        name  = "LOG_LEVEL"
        value = "DEBUG"
      },
      {
        name  = "FRONTEND_URL"
        value = var.frontend_url
      },
      {
        name  = "DATABASE_NAME"
        value = var.database_name != "" ? var.database_name : "voya_${var.environment}"
      },
      {
        name  = "ADMIN_EMAILS"
        value = var.admin_emails
      },
      {
        name  = "SENDGRID_FROM_EMAIL"
        value = var.sendgrid_from_email
      },
      {
        name  = "PORT"
        value = "80"
      },
      {
        name  = "ENABLE_DEV_TOOLS"
        value = tostring(var.enable_dev_tools)
      },
      {
        name  = "IMGPROXY_ENABLED"
        value = tostring(var.imgproxy_enabled)
      }
    ], var.additional_environment_vars)

    secrets = concat([
      {
        name      = "MONGODB_URI"
        valueFrom = var.secret_arns["MONGODB_URI"]
      },
      {
        name      = "JWT_SECRET"
        valueFrom = var.secret_arns["JWT_SECRET"]
      },
      {
        name      = "GEMINI_API_KEY"
        valueFrom = var.secret_arns["GEMINI_API_KEY"]
      },
      {
        name      = "GOOGLE_API_KEY"
        valueFrom = var.secret_arns["GOOGLE_API_KEY"]
      },
      {
        name      = "GOOGLE_MAPS_API_KEY"
        valueFrom = var.secret_arns["GOOGLE_MAPS_API_KEY"]
      },
      {
        name      = "SENDGRID_API_KEY"
        valueFrom = var.secret_arns["SENDGRID_API_KEY"]
      },
      {
        name      = "FLIGHTLOGIC_API_KEY"
        valueFrom = var.secret_arns["FLIGHTLOGIC_API_KEY"]
      },
      {
        name      = "FLIGHTLOGIC_PASSWORD"
        valueFrom = var.secret_arns["FLIGHTLOGIC_PASSWORD"]
      },
      {
        name      = "PASSENGER_ENCRYPTION_KEY"
        valueFrom = var.secret_arns["PASSENGER_ENCRYPTION_KEY"]
      }
    ], [
      for key in ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET", "LANGFUSE_SECRET_KEY", "SENTRY_DSN", "N8N_CAPABILITIES_API_KEY", "IMGPROXY_KEY", "IMGPROXY_SALT", "REVOLUT_API_KEY", "REVOLUT_PUBLIC_KEY", "REVOLUT_WEBHOOK_SECRET", "GOOGLE_OAUTH_CLIENT_ID", "OPENAI_API_KEY", "ACTIVECAMPAIGN_API_URL", "ACTIVECAMPAIGN_API_KEY"] :
      {
        name      = key
        valueFrom = lookup(var.secret_arns, key, null)
      } if lookup(var.secret_arns, key, null) != null
    ])

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:80/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-fastapi-react"
    }
  )
}

# ECS Service
resource "aws_ecs_service" "app" {
  name            = "${var.environment}-fastapi-react-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  platform_version = "LATEST"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "fastapi-react-container"
    container_port   = 80
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  enable_execute_command = var.enable_execute_command

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-fastapi-react-service"
    }
  )

  depends_on = [var.alb_listener_arn]
}

# Auto Scaling Target (optional)
resource "aws_appautoscaling_target" "ecs" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.autoscaling_max_capacity
  min_capacity       = var.autoscaling_min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU
resource "aws_appautoscaling_policy" "ecs_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-ecs-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# Auto Scaling Policy - Memory
resource "aws_appautoscaling_policy" "ecs_memory" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-ecs-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs[0].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = 80.0
  }
}
