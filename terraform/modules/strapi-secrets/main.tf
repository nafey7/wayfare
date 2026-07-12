# Strapi Secrets Module
# Creates placeholder secrets for Strapi CMS (values must be populated manually)

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.19"
    }
  }
}

locals {
  secrets = {
    "APP_KEYS"            = "Strapi app keys (comma-separated base64 values)"
    "API_TOKEN_SALT"      = "Salt for Strapi API token generation"
    "ADMIN_JWT_SECRET"    = "JWT secret for Strapi admin panel authentication"    # pragma: allowlist secret
    "TRANSFER_TOKEN_SALT" = "Salt for Strapi data transfer tokens"
    "JWT_SECRET"          = "JWT secret for Strapi Content API authentication"    # pragma: allowlist secret
  }
}

# Create secrets with placeholder values
resource "aws_secretsmanager_secret" "strapi" {
  for_each = local.secrets

  name        = "${var.environment}/Voya-strapi/${each.key}"
  description = each.value

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}/Voya-strapi/${each.key}"
    }
  )
}

# Note: Secret values must be set manually after creation
# Generate with: openssl rand -base64 32
# For APP_KEYS: two comma-separated values
resource "aws_secretsmanager_secret_version" "strapi" {
  for_each = local.secrets

  secret_id     = aws_secretsmanager_secret.strapi[each.key].id
  secret_string = "PLACEHOLDER_${each.key}_VALUE_MUST_BE_SET_MANUALLY"  # pragma: allowlist secret

  lifecycle {
    ignore_changes = [secret_string]
  }
}
