# Security Module
# Creates security groups for ALB, ECS tasks, and VPC endpoints

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.environment}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-alb-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id

  description = "Allow HTTPS from anywhere"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "alb-https-ingress"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id

  description = "Allow HTTP from anywhere (redirect to HTTPS)"
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "alb-http-ingress"
  }
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ecs" {
  security_group_id = aws_security_group.alb.id

  description                  = "Allow traffic to ECS tasks"
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "alb-to-ecs-egress"
  }
}

# Allow ALB to reach imgproxy on port 8080
resource "aws_vpc_security_group_egress_rule" "alb_to_ecs_imgproxy" {
  security_group_id = aws_security_group.alb.id

  description                  = "Allow traffic to ECS imgproxy tasks"
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "alb-to-ecs-imgproxy-egress"
  }
}

# Allow ALB to reach Strapi on port 1337
resource "aws_vpc_security_group_egress_rule" "alb_to_ecs_strapi" {
  security_group_id = aws_security_group.alb.id

  description                  = "Allow traffic to ECS Strapi tasks"
  from_port                    = 1337
  to_port                      = 1337
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "alb-to-ecs-strapi-egress"
  }
}

# ECS Task Security Group
resource "aws_security_group" "ecs" {
  name        = "${var.environment}-ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ecs-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic from ALB"
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id

  tags = {
    Name = "ecs-from-alb-ingress"
  }
}

# Allow imgproxy to receive traffic from ALB on port 8080
resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb_imgproxy" {
  security_group_id = aws_security_group.ecs.id

  description                  = "Allow imgproxy traffic from ALB"
  from_port                    = 8080
  to_port                      = 8080
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id

  tags = {
    Name = "ecs-from-alb-imgproxy-ingress"
  }
}

# Allow Strapi to receive traffic from ALB on port 1337
resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb_strapi" {
  security_group_id = aws_security_group.ecs.id

  description                  = "Allow Strapi traffic from ALB"
  from_port                    = 1337
  to_port                      = 1337
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id

  tags = {
    Name = "ecs-from-alb-strapi-ingress"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_ssm_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic from SSM VPC endpoint"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ssm_endpoint[0].id

  tags = {
    Name = "ecs-from-ssm-endpoint-ingress"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_secrets_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic from Secrets Manager VPC endpoint"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.secrets_endpoint[0].id

  tags = {
    Name = "ecs-from-secrets-endpoint-ingress"
  }
}

# ECS egress to ALB
resource "aws_vpc_security_group_egress_rule" "ecs_to_alb" {
  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic to ALB"
  from_port                    = 80
  to_port                      = 80
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id

  tags = {
    Name = "ecs-to-alb-egress"
  }
}

# ECS egress to MongoDB Atlas
resource "aws_vpc_security_group_egress_rule" "ecs_to_mongodb" {
  security_group_id = aws_security_group.ecs.id

  description = "Allow traffic to MongoDB Atlas"
  from_port   = 27017
  to_port     = 27017
  ip_protocol = "tcp"
  cidr_ipv4   = var.mongodb_cidr

  tags = {
    Name = "ecs-to-mongodb-egress"
  }
}

# ECS egress to HTTPS (Google AI, SendGrid, FlightLogic APIs)
resource "aws_vpc_security_group_egress_rule" "ecs_to_https" {
  security_group_id = aws_security_group.ecs.id

  description = "Allow HTTPS to internet for API calls"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "ecs-to-https-egress"
  }
}

# Strapi RDS Security Group
resource "aws_security_group" "strapi_rds" {
  count = var.enable_strapi_rds ? 1 : 0

  name        = "${var.environment}-strapi-rds-sg"
  description = "Security group for Strapi RDS PostgreSQL"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-strapi-rds-sg"
    }
  )
}

# RDS ingress from ECS on port 5432
resource "aws_vpc_security_group_ingress_rule" "strapi_rds_from_ecs" {
  count = var.enable_strapi_rds ? 1 : 0

  security_group_id = aws_security_group.strapi_rds[0].id

  description                  = "Allow PostgreSQL from ECS tasks"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "strapi-rds-from-ecs-ingress"
  }
}

# ECS egress to Strapi RDS on port 5432
resource "aws_vpc_security_group_egress_rule" "ecs_to_strapi_rds" {
  count = var.enable_strapi_rds ? 1 : 0

  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic to Strapi RDS"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.strapi_rds[0].id

  tags = {
    Name = "ecs-to-strapi-rds-egress"
  }
}

# ECS egress to VPC endpoints
resource "aws_vpc_security_group_egress_rule" "ecs_to_secrets_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic to Secrets Manager VPC endpoint"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.secrets_endpoint[0].id

  tags = {
    Name = "ecs-to-secrets-endpoint-egress"
  }
}

resource "aws_vpc_security_group_egress_rule" "ecs_to_ssm_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic to SSM VPC endpoint"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ssm_endpoint[0].id

  tags = {
    Name = "ecs-to-ssm-endpoint-egress"
  }
}

# SSM VPC Endpoint Security Group
resource "aws_security_group" "ssm_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  name        = "${var.environment}-ssm-endpoint-sg"
  description = "Security group for SSM VPC endpoint"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ssm-endpoint-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "ssm_endpoint_from_ecs" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ssm_endpoint[0].id

  description                  = "Allow traffic from ECS tasks"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "ssm-endpoint-from-ecs-ingress"
  }
}

resource "aws_vpc_security_group_egress_rule" "ssm_endpoint_to_ecs" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ssm_endpoint[0].id

  description                  = "Allow traffic to ECS tasks"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "ssm-endpoint-to-ecs-egress"
  }
}

# Secrets Manager VPC Endpoint Security Group
resource "aws_security_group" "secrets_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  name        = "${var.environment}-secrets-endpoint-sg"
  description = "Security group for Secrets Manager VPC endpoint"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-secrets-endpoint-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "secrets_endpoint_from_ecs" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.secrets_endpoint[0].id

  description                  = "Allow traffic from ECS tasks"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "secrets-endpoint-from-ecs-ingress"
  }
}

resource "aws_vpc_security_group_egress_rule" "secrets_endpoint_to_ecs" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.secrets_endpoint[0].id

  description                  = "Allow traffic to ECS tasks"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "secrets-endpoint-to-ecs-egress"
  }
}

# ECR VPC Endpoint Security Group
resource "aws_security_group" "ecr_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  name        = "${var.environment}-ecr-endpoint-sg"
  description = "Security group for ECR VPC endpoints"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-ecr-endpoint-sg"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "ecr_endpoint_from_ecs" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecr_endpoint[0].id

  description                  = "Allow traffic from ECS tasks"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "ecr-endpoint-from-ecs-ingress"
  }
}

resource "aws_vpc_security_group_egress_rule" "ecr_endpoint_to_ecs" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecr_endpoint[0].id

  description                  = "Allow traffic to ECS tasks"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs.id

  tags = {
    Name = "ecr-endpoint-to-ecs-egress"
  }
}

# ECS egress to ECR endpoints
resource "aws_vpc_security_group_egress_rule" "ecs_to_ecr_endpoint" {
  count = var.enable_vpc_endpoints ? 1 : 0

  security_group_id = aws_security_group.ecs.id

  description                  = "Allow traffic to ECR VPC endpoints"
  from_port                    = 443
  to_port                      = 443
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecr_endpoint[0].id

  tags = {
    Name = "ecs-to-ecr-endpoint-egress"
  }
}
