# imgproxy Module
# Deploys imgproxy as a high-performance image processing service
# See: https://docs.imgproxy.net/

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
resource "aws_cloudwatch_log_group" "imgproxy" {
  name              = "/ecs/${var.environment}-imgproxy"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-imgproxy-logs"
    }
  )
}

# ECS Task Definition
resource "aws_ecs_task_definition" "imgproxy" {
  family                   = "${var.environment}-imgproxy"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.task_execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "imgproxy"
      image = var.container_image

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "IMGPROXY_BIND"
          value = ":8080"
        },
        {
          name  = "IMGPROXY_NETWORK"
          value = "tcp"
        },
        {
          name  = "IMGPROXY_PATH_PREFIX"
          value = "/imgproxy"
        },
        # Security settings
        {
          name  = "IMGPROXY_KEY"
          value = var.imgproxy_key
        },
        {
          name  = "IMGPROXY_SALT"
          value = var.imgproxy_salt
        },
        {
          name  = "IMGPROXY_ALLOW_INSECURE_URLS"
          value = tostring(var.allow_insecure_urls)
        },
        {
          name  = "IMGPROXY_SANITIZE_SVG"
          value = "true"
        },
        # Performance settings
        {
          name  = "IMGPROXY_CONCURRENCY"
          value = tostring(var.concurrency)
        },
        {
          name  = "IMGPROXY_MAX_SRC_RESOLUTION"
          value = tostring(var.max_src_resolution)
        },
        {
          name  = "IMGPROXY_USE_ETAG"
          value = "true"
        },
        # Timeout settings
        {
          name  = "IMGPROXY_READ_TIMEOUT"
          value = "10"
        },
        {
          name  = "IMGPROXY_WRITE_TIMEOUT"
          value = "10"
        },
        {
          name  = "IMGPROXY_DOWNLOAD_TIMEOUT"
          value = "10"
        },
        # Format settings
        {
          name  = "IMGPROXY_ENABLE_WEBP_DETECTION"
          value = "true"
        },
        {
          name  = "IMGPROXY_ENABLE_AVIF_DETECTION"
          value = "true"
        },
        {
          name  = "IMGPROXY_PREFERRED_FORMATS"
          value = "avif,webp,jpeg"
        },
        # Allowed sources (if set)
        {
          name  = "IMGPROXY_ALLOWED_SOURCES"
          value = var.allowed_sources
        },
        # Cache settings - Set Cache-Control header for CDN caching
        {
          name  = "IMGPROXY_TTL"
          value = "31536000"  # 1 year - URLs are immutable (signed)
        },
        # S3 source support (e.g. private user profile photos bucket)
        {
          name  = "IMGPROXY_USE_S3"
          value = tostring(var.enable_s3_sources)
        },
        {
          name  = "IMGPROXY_S3_REGION"
          value = var.s3_region
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.imgproxy.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "imgproxy"
        }
      }

      healthCheck = {
        command     = ["CMD", "imgproxy", "health"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    }
  ])

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-imgproxy-task"
    }
  )
}

# ECS Service
resource "aws_ecs_service" "imgproxy" {
  name                   = "${var.environment}-imgproxy"
  cluster                = var.ecs_cluster_id
  task_definition        = aws_ecs_task_definition.imgproxy.arn
  desired_count          = var.desired_count
  launch_type            = "FARGATE"
  enable_execute_command = var.enable_ecs_exec

  network_configuration {
    subnets          = var.assign_public_ip ? var.public_subnet_ids : var.private_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.imgproxy.arn
    container_name   = "imgproxy"
    container_port   = 8080
  }

  depends_on = [var.alb_listener_arn]

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-imgproxy-service"
    }
  )
}

# Target Group for imgproxy
resource "aws_lb_target_group" "imgproxy" {
  name        = "${var.environment}-imgproxy"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  dynamic "health_check" {
    for_each = var.enable_health_checks ? [1] : []
    content {
      enabled             = true
      healthy_threshold   = 2
      unhealthy_threshold = 3
      timeout             = 5
      interval            = 30
      port                = "traffic-port"
      path                = "/health"
      matcher             = "200"
    }
  }

  deregistration_delay = 30

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-imgproxy-tg"
    }
  )
}

# ALB Listener Rule for imgproxy (path-based routing)
resource "aws_lb_listener_rule" "imgproxy" {
  listener_arn = var.alb_https_listener_arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.imgproxy.arn
  }

  condition {
    path_pattern {
      values = ["/imgproxy/*"]
    }
  }

  priority = 95  # Higher priority than default routes

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-imgproxy-rule"
    }
  )
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "imgproxy" {
  count = var.enable_autoscaling ? 1 : 0

  max_capacity       = var.autoscaling_max_capacity
  min_capacity       = var.autoscaling_min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.imgproxy.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - CPU (primary scaling metric for image processing)
resource "aws_appautoscaling_policy" "imgproxy_cpu" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-imgproxy-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.imgproxy[0].resource_id
  scalable_dimension = aws_appautoscaling_target.imgproxy[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.imgproxy[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = var.autoscaling_cpu_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Auto Scaling Policy - Memory (secondary metric)
resource "aws_appautoscaling_policy" "imgproxy_memory" {
  count = var.enable_autoscaling ? 1 : 0

  name               = "${var.environment}-imgproxy-memory-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.imgproxy[0].resource_id
  scalable_dimension = aws_appautoscaling_target.imgproxy[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.imgproxy[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = var.autoscaling_memory_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
