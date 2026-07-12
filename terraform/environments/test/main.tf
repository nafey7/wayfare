# Test Environment Configuration
# Orchestrates all modules to create complete test infrastructure

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
    key            = "test/terraform.tfstate"
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
  environment    = "test"
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
  enable_execute_command    = var.enable_ecs_exec
  enable_autoscaling        = var.enable_autoscaling
  autoscaling_min_capacity  = var.autoscaling_min_capacity
  autoscaling_max_capacity  = var.autoscaling_max_capacity

  additional_environment_vars = [
    {
      name  = "BACKEND_URL"
      value = "https://test.myvoya.ai"
    },
    {
      name  = "CORS_ORIGINS"
      value = "[\"https://test.myvoya.ai\"]"
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
      value = "https://test.myvoya.ai"
    },
    {
      name  = "N8N_ITINERARY_WEBHOOK_URL"
      value = "https://voya-ai.app.n8n.cloud/webhook/itinerary-agent-test"
    },
    # Langfuse LLM Observability
    {
      name  = "LANGFUSE_ENABLED"
      value = "true"
    },
    {
      name  = "LANGFUSE_PUBLIC_KEY"
      value = "pk-lf-2465e392-ad64-449f-a3e1-31a37643f664"
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
    # Toggle: aws ssm put-parameter --name /voya/test/feature-flags/public-chat --value false --overwrite --profile voya-admin
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
    # Sentry Configuration (100% sampling for test)
    {
      name  = "SENTRY_TRACES_SAMPLE_RATE"
      value = "1.0"
    },
    {
      name  = "SENTRY_PROFILES_SAMPLE_RATE"
      value = "1.0"
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
      value = "gpt-5.4-nano"
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
      # false: no post-search revalidation on flight search API in test env.
      name  = "FLIGHT_SEARCH_CONCURRENT_REVALIDATION"
      value = "false"
    }
  ]

  tags = var.common_tags
}
