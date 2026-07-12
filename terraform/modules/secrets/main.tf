# Secrets Manager Module
# Creates placeholder secrets (values must be populated manually)

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
    "MONGODB_URI"          = "MongoDB connection string for staging database"
    "JWT_SECRET"           = "JWT signing key (min 32 characters)"
    "GEMINI_API_KEY"       = "Google Gemini API key"
    "GOOGLE_API_KEY"       = "Google API key"
    "GOOGLE_MAPS_API_KEY"  = "Google Maps JavaScript API key for client-side map rendering"  # pragma: allowlist secret
    "SENDGRID_API_KEY"     = "SendGrid email service API key"
    "FLIGHTLOGIC_API_KEY"  = "FlightLogic travel API key (test credentials)"
    "FLIGHTLOGIC_PASSWORD" = "FlightLogic API password"
    "STRIPE_SECRET_KEY"    = "Stripe secret API key"
    "STRIPE_PUBLISHABLE_KEY" = "Stripe publishable API key"
    "STRIPE_WEBHOOK_SECRET" = "Stripe webhook signing secret"
    "REVOLUT_API_KEY"       = "Revolut Merchant API key"  # pragma: allowlist secret
    "REVOLUT_PUBLIC_KEY"    = "Revolut public key for client-side integration"  # pragma: allowlist secret
    "REVOLUT_WEBHOOK_SECRET" = "Revolut webhook signing secret"  # pragma: allowlist secret
    "LANGFUSE_SECRET_KEY"  = "Langfuse secret key for LLM observability"  # pragma: allowlist secret
    "SENTRY_DSN"           = "Sentry DSN for backend error tracking"
    "SENTRY_DSN_FRONTEND"  = "Sentry DSN for frontend error tracking"
    "N8N_CAPABILITIES_API_KEY" = "API key for n8n Cloud to call Capabilities API endpoints"  # pragma: allowlist secret
    "IMGPROXY_KEY"         = "imgproxy URL signing key (hex-encoded, 32 bytes)"  # pragma: allowlist secret
    "IMGPROXY_SALT"        = "imgproxy URL signing salt (hex-encoded, 32 bytes)"  # pragma: allowlist secret
    "GOOGLE_OAUTH_CLIENT_ID" = "Google OAuth client ID for Sign in with Google"
    "PASSENGER_ENCRYPTION_KEY" = "Fernet key for encrypting sensitive passenger PII (passport, frequent flyer numbers)"  # pragma: allowlist secret
    "OPENAI_API_KEY"           = "OpenAI API key for LLM capabilities"  # pragma: allowlist secret
    "SLACK_WEBHOOK_URL"        = "Slack Incoming Webhook URL for booking/ticket API error notifications"
    "VITE_STRAPI_API_TOKEN"    = "Strapi CMS API token for frontend content requests"  # pragma: allowlist secret
    "TURNSTILE_SECRET_KEY"     = "Cloudflare Turnstile secret key for server-side token verification (gates /api/places after chat-driven itinerary)"  # pragma: allowlist secret
    "TURNSTILE_SITEKEY"        = "Cloudflare Turnstile public sitekey (also exposed to frontend as VITE_TURNSTILE_SITEKEY)"  # pragma: allowlist secret
    "ACTIVECAMPAIGN_API_URL"   = "ActiveCampaign account API base URL (e.g. https://<account>.api-us1.com)"
    "ACTIVECAMPAIGN_API_KEY"   = "ActiveCampaign API token for syncing new signups to CRM"  # pragma: allowlist secret
  }
}

# Create secrets with placeholder values
resource "aws_secretsmanager_secret" "app" {
  for_each = local.secrets

  name        = "${var.environment}/Voya-fastAPI/${each.key}"
  description = each.value

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}/Voya-fastAPI/${each.key}"
    }
  )
}

# Note: Secret values must be set manually after creation
# Use: aws secretsmanager put-secret-value --secret-id <name> --secret-string <value>
# Or through AWS Console
resource "aws_secretsmanager_secret_version" "app" {
  for_each = local.secrets

  secret_id     = aws_secretsmanager_secret.app[each.key].id
  secret_string = "PLACEHOLDER_${each.key}_VALUE_MUST_BE_SET_MANUALLY"

  lifecycle {
    ignore_changes = [secret_string]
  }
}
