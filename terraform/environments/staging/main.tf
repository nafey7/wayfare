# Staging Environment Configuration
# Orchestrates all modules to create complete staging infrastructure

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }

  backend "s3" {
    bucket         = "voya-terraform-state-155304839180"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "voya-terraform-locks"
    encrypt        = true
    # profile: omitted so OIDC works in CI. For local use:
    #   terraform init -backend-config="profile=voya-poweruser"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = var.common_tags
  }
}

# Local variables
locals {
  environment    = "staging"
  aws_account_id = "155304839180"
}

# =============================================================================
# Feature Flags (SSM Parameter Store)
# =============================================================================

resource "aws_ssm_parameter" "feature_flag_public_chat" {
  name  = "/voya/${local.environment}/feature-flags/public-chat"
  type  = "String"
  value = "true"

  lifecycle {
    ignore_changes = [value]
  }

  tags = var.common_tags
}

# Networking Module
module "networking" {
  source = "../../modules/networking"

  environment        = local.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = true
  enable_vpc_endpoints = true
  aws_region         = var.aws_region

  tags = var.common_tags
}

# Security Module
module "security" {
  source = "../../modules/security"

  environment          = local.environment
  vpc_id               = module.networking.vpc_id
  mongodb_cidr         = var.mongodb_cidr
  enable_vpc_endpoints = true
  enable_strapi_rds    = true

  tags = var.common_tags
}

# Associate VPC endpoints with security groups
resource "aws_vpc_endpoint_security_group_association" "secretsmanager" {
  vpc_endpoint_id   = module.networking.secretsmanager_endpoint_id
  security_group_id = module.security.secrets_endpoint_security_group_id
}

resource "aws_vpc_endpoint_security_group_association" "ssm" {
  vpc_endpoint_id   = module.networking.ssm_endpoint_id
  security_group_id = module.security.ssm_endpoint_security_group_id
}

# IAM Module
module "iam" {
  source = "../../modules/iam"

  environment                 = local.environment
  aws_region                  = var.aws_region
  aws_account_id              = local.aws_account_id
  enable_ssm_session_manager  = var.enable_ssm_session_manager
  enable_strapi_s3            = true
  enable_strapi_secrets       = true

  tags = var.common_tags
}

# ECR Module
module "ecr" {
  source = "../../modules/ecr"

  environment           = local.environment
  image_retention_count = var.ecr_image_retention_count
  scan_on_push          = true

  tags = var.common_tags
}

# Secrets Module
module "secrets" {
  source = "../../modules/secrets"

  environment = local.environment

  tags = var.common_tags
}

# ALB Module
module "alb" {
  source = "../../modules/alb"

  environment              = local.environment
  vpc_id                   = module.networking.vpc_id
  public_subnet_ids        = module.networking.public_subnet_ids
  alb_security_group_id    = module.security.alb_security_group_id
  certificate_arn          = var.acm_certificate_arn
  enable_deletion_protection = false

  tags = var.common_tags
}

# GitHub OIDC Module
# NOTE: This updates a GLOBAL IAM role shared across all environments.
# ALL environment role ARNs must be included to prevent breaking other deployments.
module "github_oidc" {
  source = "../../modules/github-oidc"

  github_org = "myvoya"
  github_repo = "voya"
  ecs_task_execution_role_arns = [
    "arn:aws:iam::${local.aws_account_id}:role/staging-ecs-task-execution-role",
    "arn:aws:iam::${local.aws_account_id}:role/test-ecs-task-execution-role",
    "arn:aws:iam::${local.aws_account_id}:role/production-ecs-task-execution-role",
  ]
  ecs_task_role_arns = [
    "arn:aws:iam::${local.aws_account_id}:role/staging-ecs-task-role",
    "arn:aws:iam::${local.aws_account_id}:role/test-ecs-task-role",
    "arn:aws:iam::${local.aws_account_id}:role/production-ecs-task-role",
  ]

  tags = var.common_tags
}

# ECS Module
module "ecs" {
  source = "../../modules/ecs"

  environment               = local.environment
  vpc_id                    = module.networking.vpc_id
  private_subnet_ids        = module.networking.private_subnet_ids
  ecs_security_group_id     = module.security.ecs_security_group_id
  target_group_arn          = module.alb.target_group_arn
  alb_listener_arn          = module.alb.http_listener_arn
  task_execution_role_arn   = module.iam.ecs_task_execution_role_arn
  task_role_arn             = module.iam.ecs_task_role_arn
  ecr_repository_url        = module.ecr.repository_url
  container_image_tag       = var.container_image_tag
  task_cpu                  = var.ecs_task_cpu
  task_memory               = var.ecs_task_memory
  desired_count             = var.ecs_desired_count
  log_group_name            = "/ecs/${local.environment}-voya-backend"
  aws_region                = var.aws_region
  secret_arns               = module.secrets.secret_arns
  frontend_url              = var.frontend_url
  admin_emails              = var.admin_emails
  sendgrid_from_email       = var.sendgrid_from_email
  debug_mode                = true
  enable_dev_tools          = true
  imgproxy_enabled          = var.imgproxy_enabled
  enable_execute_command    = var.enable_ecs_exec
  enable_autoscaling        = var.enable_autoscaling
  autoscaling_min_capacity  = var.autoscaling_min_capacity
  autoscaling_max_capacity  = var.autoscaling_max_capacity

  additional_environment_vars = [
    {
      name  = "BACKEND_URL"
      value = "https://staging.myvoya.ai"
    },
    {
      name  = "CORS_ORIGINS"
      value = "[\"https://staging.myvoya.ai\"]"
    },
    {
      name  = "FLIGHTLOGIC_ACCESS_TYPE"
      value = "Test"
    },
    {
      name  = "FLIGHTLOGIC_API_URL"
      value = "https://travelnext.works/api/aeroVE5"
    },
    {
      name  = "FLIGHTLOGIC_FLIGHTS_API_BASE_URL"
      value = "https://travelnext.works/api/aeroVE5"
    },
    {
      name  = "FLIGHTLOGIC_HOTELS_API_BASE_URL"
      value = "https://travelnext.works/api/hotel-api-v6"
    },
    {
      name  = "FLIGHTLOGIC_IP_ADDRESS"
      value = "98.89.125.207"
    },
    {
      name  = "FLIGHTLOGIC_USER_ID"
      value = "myvoya_testAPI"
    },
    {
      name  = "REACT_APP_API_URL"
      value = "https://staging.myvoya.ai"
    },
    {
      name  = "N8N_ITINERARY_WEBHOOK_URL"
      value = "https://voya-ai.app.n8n.cloud/webhook/itinerary-agent-staging"
    },
    # Langfuse LLM Observability
    {
      name  = "LANGFUSE_ENABLED"
      value = "true"
    },
    {
      name  = "LANGFUSE_PUBLIC_KEY"
      value = "pk-lf-d43d055c-0d45-4a67-86b7-33e5bd0f76fa"
    },
    {
      name  = "LANGFUSE_BASE_URL"
      value = "https://cloud.langfuse.com"
    },
    # LangGraph Feature Flags
    {
      name  = "VOYA_FEATURE_FLAG_USE_LANGGRAPH_FLIGHTS"
      value = "true"
    },
    {
      name  = "VOYA_FEATURE_FLAG_USE_LANGGRAPH_HOTELS"
      value = "true"
    },
    {
      name  = "VOYA_FEATURE_FLAG_USE_LANGGRAPH_ROUTER"
      value = "false"
    },
    {
      name  = "VOYA_FEATURE_FLAG_USE_LANGGRAPH_ITINERARY"
      value = "true"
    },
    {
      name  = "VOYA_FEATURE_FLAG_USE_LANGGRAPH_ITINERARY_V2"
      value = "true"
    },
    {
      name  = "VOYA_FEATURE_FLAG_CHAT_FEEDBACK"
      value = "true"
    },
    {
      name  = "VOYA_FEATURE_FLAG_USE_V2_SUPERVISOR"
      value = "true"
    },
    {
      name  = "VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS"
      value = "false"
    },
    # VOYA_FEATURE_FLAG_PUBLIC_CHAT: managed via SSM Parameter Store
    # Toggle: aws ssm put-parameter --name /voya/staging/feature-flags/public-chat --value false --overwrite --profile voya-admin
    {
      name  = "PUBLIC_CHAT_MESSAGES_PER_MINUTE"
      value = "7"
    },
    {
      name  = "RATE_LIMIT_ENABLED"
      value = "true"
    },
    {
      name  = "TRUST_X_FORWARDED_FOR"
      value = "true"
    },
    # LLM Model Configuration (per-agent provider, model, and fallback)
    {
      name  = "LLM_SUPERVISOR_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_SUPERVISOR_MODEL"
      value = "gpt-5.4-nano"
    },
    {
      name  = "LLM_SUPERVISOR_FALLBACK_MODEL"
      value = "gpt-5.4-mini"
    },
    {
      name  = "LLM_AGENT_GENERAL_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_AGENT_GENERAL_MODEL"
      value = "gpt-5.4-mini"
    },
    {
      name  = "LLM_AGENT_GENERAL_FALLBACK_MODEL"
      value = "gpt-5.4-nano"
    },
    {
      name  = "LLM_AGENT_FLIGHT_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_AGENT_FLIGHT_MODEL"
      value = "gpt-5.4-mini"
    },
    {
      name  = "LLM_AGENT_FLIGHT_FALLBACK_MODEL"
      value = "gpt-5.4-nano"
    },
    {
      name  = "LLM_AGENT_HOTEL_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_AGENT_HOTEL_MODEL"
      value = "gpt-5.4-mini"
    },
    {
      name  = "LLM_AGENT_HOTEL_FALLBACK_MODEL"
      value = "gpt-5.4-nano"
    },
    {
      name  = "LLM_AGENT_ITINERARY_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_AGENT_ITINERARY_MODEL"
      value = "gpt-5.4-mini"
    },
    {
      name  = "LLM_AGENT_ITINERARY_FALLBACK_MODEL"
      value = "gpt-5.4-nano"
    },
    {
      name  = "LLM_TOOL_DATES_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_TOOL_DATES_MODEL"
      value = "gpt-5.4-mini"
    },
    {
      name  = "LLM_TOOL_BUDGET_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_TOOL_BUDGET_MODEL"
      value = "gpt-5.4-nano"
    },
    {
      name  = "LLM_TOOL_ITINERARY_PROVIDER"
      value = "openai"
    },
    {
      name  = "LLM_TOOL_ITINERARY_MODEL"
      value = "gpt-5.4-mini"
    },
    # Sentry Configuration (100% sampling for staging)
    {
      name  = "SENTRY_TRACES_SAMPLE_RATE"
      value = "1.0"
    },
    {
      name  = "SENTRY_PROFILES_SAMPLE_RATE"
      value = "1.0"
    },
    # imgproxy Configuration
    # Uses CDN subdomain to avoid cache purge on app deployments
    {
      name  = "IMGPROXY_URL"
      value = "https://cdn-staging.myvoya.ai/imgproxy"
    },
    # Payment Provider Configuration (Revolut)
    {
      name  = "PAYMENT_PROVIDER"
      value = "revolut"
    },
    {
      name  = "REVOLUT_MERCHANT_ID"
      value = "merchant_1234567890abcdef"
    },
    {
      name  = "REVOLUT_API_BASE_URL"
      value = "https://sandbox-merchant.revolut.com/api"
    },
    {
      name  = "REVOLUT_ENVIRONMENT"
      value = "sandbox"
    },
    {
      # false: no post-search revalidation on flight search API. Set true to test revalidation in staging.
      name  = "FLIGHT_SEARCH_CONCURRENT_REVALIDATION"
      value = "false"
    },
    # User profile photos (S3 + imgproxy)
    {
      name  = "S3_PHOTOS_BUCKET"
      value = module.photos_bucket.bucket_name
    },
    {
      name  = "S3_PHOTOS_REGION"
      value = var.aws_region
    }
  ]

  tags = var.common_tags
}

# User profile photos bucket (private S3, read by imgproxy via s3:// source).
module "photos_bucket" {
  source = "../../modules/photos_bucket"

  environment            = local.environment
  backend_task_role_name = module.iam.ecs_task_role_name
  # Backend and imgproxy share the task role; module is a no-op for imgproxy when names match.
  imgproxy_task_role_name = module.iam.ecs_task_role_name

  cors_allowed_origins = [
    "https://staging.myvoya.ai",
    "https://www.myvoya.ai",
    "https://myvoya.ai",
  ]

  tags = var.common_tags
}

# imgproxy Module - High-performance image processing
# Replaces in-app image proxy for better performance and resource isolation
module "imgproxy" {
  source = "../../modules/imgproxy"

  # Use ECR to avoid Docker Hub rate limits
  container_image         = "155304839180.dkr.ecr.us-east-1.amazonaws.com/myvoya-staging-imgproxy:latest"

  environment             = local.environment
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  public_subnet_ids       = module.networking.public_subnet_ids
  ecs_cluster_id          = module.ecs.cluster_id
  ecs_cluster_name        = module.ecs.cluster_name
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn
  security_group_id       = module.security.ecs_security_group_id
  alb_https_listener_arn  = module.alb.https_listener_arn
  alb_listener_arn        = module.alb.http_listener_arn

  # Task sizing (small - imgproxy is efficient)
  task_cpu     = var.imgproxy_task_cpu
  task_memory  = var.imgproxy_task_memory
  desired_count = var.imgproxy_desired_count

  # Security: Signing keys must match backend's IMGPROXY_KEY/IMGPROXY_SALT secrets
  # These values are stored in AWS Secrets Manager for the backend, passed here for imgproxy
  imgproxy_key        = "086626687af0a86b14a451dc9e8f972d603007d2fc97492a9b60ac3ce33a3429"
  imgproxy_salt       = "6de2c1a5fa1656658bc01527ab3981b027ae760f1e0a85d7cde81622c5bef40b"
  allow_insecure_urls = var.imgproxy_allow_insecure_urls

  # Allowed source domains (hotel/flight image CDNs + private S3 photos bucket).
  # imgproxy's whitelist applies before the protocol handler, so signed
  # s3://${module.photos_bucket.bucket_name}/... URLs need an explicit prefix.
  allowed_sources = join(",", [
    "https://dynamic-media-cdn.tripadvisor.com",
    "https://media-cdn.tripadvisor.com",
    "https://cf.bstatic.com",
    "https://photos.hotelbeds.com",
    "https://i.travelapi.com",
    "https://images.unsplash.com",
    "https://images.kiwi.com",
    "https://cdn.tourismcloudservice.com",
    "s3://${module.photos_bucket.bucket_name}/",
  ])

  enable_ecs_exec = var.enable_ecs_exec

  # Enable s3:// source support so imgproxy can fetch user profile photos.
  enable_s3_sources = true
  s3_region         = var.aws_region

  tags = var.common_tags
}

# Add wildcard cert to staging ALB for Strapi subdomains (cms-staging, strapi-media-staging)
# The staging cert only covers staging.myvoya.ai, not other subdomains
resource "aws_lb_listener_certificate" "wildcard" {
  listener_arn    = module.alb.https_listener_arn
  certificate_arn = "arn:aws:acm:us-east-1:155304839180:certificate/358296c6-21e2-407c-a506-ef3d74b2e301"
}

# --- Strapi CMS ---

# Strapi ECR Repository
resource "aws_ecr_repository" "strapi" {
  name                 = "myvoya-${local.environment}-strapi"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.common_tags, { Name = "myvoya-${local.environment}-strapi" })
}

resource "aws_ecr_lifecycle_policy" "strapi" {
  repository = aws_ecr_repository.strapi.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# Strapi Secrets
module "strapi_secrets" {
  source = "../../modules/strapi-secrets"

  environment = local.environment
  tags        = var.common_tags
}

# Strapi RDS (PostgreSQL)
module "strapi_rds" {
  source = "../../modules/strapi-rds"

  environment           = local.environment
  private_subnet_ids    = module.networking.private_subnet_ids
  rds_security_group_id = module.security.strapi_rds_security_group_id
  instance_class        = "db.t4g.micro"
  allocated_storage     = 20
  multi_az              = false
  backup_retention_period = 7
  deletion_protection   = false
  skip_final_snapshot   = true
  apply_immediately     = true

  tags = var.common_tags
}

# Strapi Media (S3 + CloudFront)
# Note: Uses production wildcard cert (*.myvoya.ai) for CloudFront
# because the staging cert only covers staging.myvoya.ai
module "strapi_media" {
  source = "../../modules/strapi-media"

  environment         = local.environment
  acm_certificate_arn = "arn:aws:acm:us-east-1:155304839180:certificate/358296c6-21e2-407c-a506-ef3d74b2e301"
  media_domain_name   = "strapi-media-staging.myvoya.ai"
  cors_allowed_origins = ["https://cms-staging.myvoya.ai"]

  tags = var.common_tags
}

# Strapi CMS (ECS Service)
module "strapi" {
  source = "../../modules/strapi"

  environment            = local.environment
  aws_region             = var.aws_region
  vpc_id                 = module.networking.vpc_id
  private_subnet_ids     = module.networking.private_subnet_ids
  ecs_cluster_id         = module.ecs.cluster_id
  ecs_cluster_name       = module.ecs.cluster_name
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn          = module.iam.ecs_task_role_arn
  security_group_id      = module.security.ecs_security_group_id
  alb_https_listener_arn = module.alb.https_listener_arn
  alb_listener_arn       = module.alb.http_listener_arn

  container_image = "${aws_ecr_repository.strapi.repository_url}:latest"
  task_cpu        = 512
  task_memory     = 1024
  desired_count   = 1

  cms_domain  = "cms-staging.myvoya.ai"
  app_url     = "https://cms-staging.myvoya.ai"
  db_address  = module.strapi_rds.db_address
  db_port     = module.strapi_rds.db_port
  db_name     = module.strapi_rds.db_name
  db_username = module.strapi_rds.db_username
  db_master_user_secret_arn = module.strapi_rds.db_master_user_secret_arn
  s3_bucket_name = module.strapi_media.s3_bucket_name
  cdn_url     = "https://strapi-media-staging.myvoya.ai"
  secret_arns = module.strapi_secrets.secret_arns
  sendgrid_api_key_arn = module.secrets.secret_arns["SENDGRID_API_KEY"]
  sendgrid_from_email  = var.sendgrid_from_email

  enable_autoscaling = false
  enable_ecs_exec    = var.enable_ecs_exec
  log_retention_days = 30

  tags = var.common_tags
}
