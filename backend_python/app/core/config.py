import logging
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core import security_constants


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings for env‑management."""

    # ================== APPLICATION CORE ==================
    APP_NAME: str = Field(default="Voya API")
    VERSION: str = Field(default="1.0.0")
    GIT_COMMIT_HASH: str = Field(default="unknown")
    GIT_VERSION: str = Field(
        default="unknown"
    )  # From git describe --tags (e.g., v2026.1.1-3-g4620075)
    ENVIRONMENT: str = Field(default="development")  # development, staging, production
    DEBUG: bool = Field(default=False)  # overridden by ENV
    HOST: str = Field(default="0.0.0.0")  # nosec B104 - Safe for Docker containers with network isolation
    PORT: int = Field(default=8000)

    # ================== SECURITY ==================
    SECRET_KEY: str = Field(
        default="dev-secret-key-please-change-in-production",
        description="JWT signing key - override in prod",
    )
    PASSENGER_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description="Fernet key for encrypting sensitive passenger PII (passport, FF numbers). "
        'Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())". '
        "Required for passenger storage. In production, prefer AWS Secrets Manager.",
    )
    ALGORITHM: str = Field(default=security_constants.JWT_ALGORITHM)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=security_constants.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=security_constants.REFRESH_TOKEN_EXPIRE_DAYS
    )
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = Field(
        default=security_constants.EMAIL_VERIFICATION_EXPIRE_DAYS * 24
    )
    PASSWORD_RESET_EXPIRE_HOURS: int = Field(
        default=security_constants.PASSWORD_RESET_EXPIRE_HOURS
    )
    OTP_EXPIRE_MINUTES: int = Field(default=security_constants.OTP_EXPIRE_MINUTES)
    MAX_LOGIN_ATTEMPTS: int = Field(default=security_constants.MAX_LOGIN_ATTEMPTS)
    ACCOUNT_LOCKOUT_MINUTES: int = Field(
        default=security_constants.ACCOUNT_LOCKOUT_MINUTES
    )

    # ================== DATABASE ==================
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = Field(default="voya")
    DATABASE_MAX_POOL_SIZE: int = Field(default=10)
    DATABASE_MIN_POOL_SIZE: int = Field(default=1)

    # ================== CORS & FRONTEND ==================
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:5000,https://app.myvoya.ai,https://www.myvoya.ai",
        alias="CORS_ORIGINS",
    )

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Convert CORS_ORIGINS string to list"""
        if isinstance(self.cors_origins_raw, str):
            if not self.cors_origins_raw.strip():
                return [
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "http://localhost:5000",
                    "https://app.myvoya.ai",
                    "https://www.myvoya.ai",
                ]
            return [
                origin.strip()
                for origin in self.cors_origins_raw.split(",")
                if origin.strip()
            ]
        return self.cors_origins_raw if isinstance(self.cors_origins_raw, list) else []

    FRONTEND_URL: str = Field(default="http://localhost:3000")
    BACKEND_URL: str = Field(
        default="http://localhost:8000",
        description="Backend URL for dev tools like flight-booker",
    )
    PRODUCTION_FRONTEND_URL: str = Field(default="https://www.myvoya.ai")
    STAGING_FRONTEND_URL: str = Field(default="https://staging.myvoya.ai")

    model_config = SettingsConfigDict(
        env_file=".env",  # load .env during development
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Prevent automatic JSON parsing for complex types
        env_parse_none_str="None",
    )

    # ================== EXTERNAL APIS - AI ==================
    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google Gemini API key for AI/chatbot services (Gemini models)",
    )
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key for GPT models",
    )
    XAI_API_KEY: str | None = Field(
        default=None,
        description="xAI API key for Grok models",
    )
    AWS_BEARER_TOKEN_BEDROCK: str | None = Field(
        default=None,
        description="AWS Bedrock bearer token for API key auth (DeepSeek, Qwen, Mistral)",
    )
    AWS_REGION: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock API",
    )

    # ================== LLM COMPONENT CONFIGURATION ==================
    # Per-component provider/model overrides. Defaults: gemini/gemini-2.5-pro
    # Format: LLM_{COMPONENT}_PROVIDER=gemini|openai|xai|bedrock
    #         LLM_{COMPONENT}_MODEL=model-name
    LLM_SUPERVISOR_PROVIDER: str | None = Field(default=None)
    LLM_SUPERVISOR_MODEL: str | None = Field(default=None)
    LLM_SUPERVISOR_FALLBACK_MODEL: str | None = Field(default=None)
    LLM_AGENT_FLIGHT_PROVIDER: str | None = Field(default=None)
    LLM_AGENT_FLIGHT_MODEL: str | None = Field(default=None)
    LLM_AGENT_FLIGHT_FALLBACK_MODEL: str | None = Field(default=None)
    LLM_AGENT_HOTEL_PROVIDER: str | None = Field(default=None)
    LLM_AGENT_HOTEL_MODEL: str | None = Field(default=None)
    LLM_AGENT_HOTEL_FALLBACK_MODEL: str | None = Field(default=None)
    LLM_AGENT_ITINERARY_PROVIDER: str | None = Field(default=None)
    LLM_AGENT_ITINERARY_MODEL: str | None = Field(default=None)
    LLM_AGENT_ITINERARY_FALLBACK_MODEL: str | None = Field(default=None)
    LLM_AGENT_GENERAL_PROVIDER: str | None = Field(default=None)
    LLM_AGENT_GENERAL_MODEL: str | None = Field(default=None)
    LLM_AGENT_GENERAL_FALLBACK_MODEL: str | None = Field(default=None)
    LLM_TOOL_DATES_PROVIDER: str | None = Field(default=None)
    LLM_TOOL_DATES_MODEL: str | None = Field(default=None)
    LLM_TOOL_ITINERARY_PROVIDER: str | None = Field(default=None)
    LLM_TOOL_ITINERARY_MODEL: str | None = Field(default=None)
    LLM_TOOL_BUDGET_PROVIDER: str | None = Field(default=None)
    LLM_TOOL_BUDGET_MODEL: str | None = Field(default=None)

    # ================== EXTERNAL APIS - GOOGLE SERVICES ==================
    GOOGLE_API_KEY: str | None = Field(
        default=None,
        description="Google API key for non-AI services (Maps, Geocoding, Places, etc.)",
    )
    GOOGLE_MAPS_API_KEY: str | None = Field(
        default=None,
        description="Google Maps JavaScript API key for client-side map rendering",
    )
    PLACES_API_ENABLED: bool = Field(
        default=True,
        description="Global kill-switch for Google Places API. When False, all "
        "Places calls (itinerary image enrichment, /api/places/*, "
        "/api/public/places/*) are short-circuited regardless of API key presence.",
    )
    GOOGLE_OAUTH_CLIENT_ID: str | None = Field(
        default=None,
        description="Google Sign-In client ID",
    )
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = Field(
        default=None,
        description="Google Service Account JSON credentials (base64 encoded or raw JSON)",
    )

    # ================== EXTERNAL APIS - FLIGHTLOGIC ==================
    FLIGHTLOGIC_API_URL: str | None = Field(
        default=None,
        description="DEPRECATED: Use FLIGHTLOGIC_FLIGHTS_API_BASE_URL instead. Base URL for FlightLogic API (for backward compatibility)",
    )
    FLIGHTLOGIC_FLIGHTS_API_BASE_URL: str = Field(
        default="https://travelnext.works/api/aeroVE5",
        description="Base URL for FlightLogic Flights API (aeroVE5 endpoint)",
    )
    FLIGHTLOGIC_HOTELS_API_BASE_URL: str = Field(
        default="https://travelnext.works/api/hotel-api-v6",
        description="Base URL for FlightLogic Hotels API (hotel-api-v6 endpoint)",
    )
    FLIGHTLOGIC_API_KEY: str | None = Field(
        default=None,
        description="FlightLogic API key",
    )
    FLIGHTLOGIC_USER_ID: str | None = Field(
        default=None,
        description="FlightLogic user ID",
    )
    FLIGHTLOGIC_PASSWORD: str | None = Field(
        default=None,
        description="FlightLogic password",
    )
    FLIGHTLOGIC_ACCESS_TYPE: str = Field(
        default="Test",
        description="Test or Production access",
    )
    FLIGHTLOGIC_IP_ADDRESS: str | None = Field(
        default=None,
        description="IP address of the FlightLogic instance",
    )
    FLIGHTLOGIC_SPOOF_IP: str | None = Field(
        default=None,
        description="IP address to spoof in X-Forwarded-For header (for local development bypassing IP whitelist)",
    )

    # ================== IMGPROXY (External Image Processing) ==================
    IMGPROXY_ENABLED: bool = Field(
        default=False,
        description="Enable imgproxy URL signing for external images. "
        "When enabled, hotel/flight image URLs are transformed to signed imgproxy URLs.",
    )
    IMGPROXY_URL: str = Field(
        default="/imgproxy",
        description="Base URL for imgproxy. Use CDN subdomain in production "
        "(e.g., https://cdn.myvoya.ai/imgproxy) to avoid cache invalidation on app deploys.",
    )
    IMGPROXY_KEY: str | None = Field(
        default=None,
        description="imgproxy signing key (hex-encoded). "
        "Generate with: openssl rand -hex 32",
    )
    IMGPROXY_SALT: str | None = Field(
        default=None,
        description="imgproxy signing salt (hex-encoded). "
        "Generate with: openssl rand -hex 32",
    )
    IMAGE_PROXY_ALLOW_ALL_DOMAINS: bool = Field(
        default=False,
        description="When True, /api image proxy allows any external domain (still blocks "
        "localhost/internal IPs). When False, only the allowlist in app.api.proxy applies.",
    )

    # ================== S3 (USER PROFILE PHOTOS) ==================
    S3_PHOTOS_BUCKET: str | None = Field(
        default=None,
        description="Private S3 bucket for user profile photo originals. "
        "Set per env (myvoya-${env}-photos). When unset, photo upload is disabled.",
    )
    S3_PHOTOS_REGION: str = Field(
        default="us-east-1",
        description="Region of the S3 photos bucket. Used to build s3:// source URLs for imgproxy.",
    )
    S3_ENDPOINT_URL: str | None = Field(
        default=None,
        description="Override S3 endpoint (e.g. http://minio:9000 for local). "
        "Unset in cloud → boto3 uses real AWS.",
    )
    S3_FORCE_PATH_STYLE: bool = Field(
        default=False,
        description="Force path-style S3 addressing (required for MinIO). "
        "False in cloud uses default virtual-host style.",
    )
    AVATAR_MAX_BYTES: int = Field(
        default=5 * 1024 * 1024,
        description="Maximum profile photo upload size in bytes (default 5 MiB).",
    )
    AVATAR_ALLOWED_MIME: str = Field(
        default="image/jpeg,image/png,image/webp",
        description="Comma-separated list of accepted profile photo MIME types.",
    )
    AVATAR_MAX_DIMENSION: int = Field(
        default=4096,
        description="Maximum width/height in pixels for a decoded profile photo. "
        "Guards against decompression-bomb inputs.",
    )

    # ================== SLACK NOTIFICATIONS ==================
    SLACK_WEBHOOK_URL: str | None = Field(
        default=None,
        description="Slack Incoming Webhook URL for booking/ticket API error notifications. "
        "When set, errors from flight booking, issue_ticket, and hotel booking are posted to Slack.",
    )
    GDS_TICKET_TIME_LIMIT_ALERT_WINDOW_HOURS: int = Field(
        default=2,
        ge=1,
        le=168,
        description="GDS ticket time limit job: alert when deadline is within this many hours (hourly ECS task).",
    )
    GDS_TICKET_TIME_LIMIT_ALERT_LEASE_MINUTES: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="Mongo lease on a booking_events row while sending Slack; avoids duplicate alerts from overlapping job runs.",
    )

    # ================== N8N INTEGRATION ==================
    N8N_ITINERARY_WEBHOOK_URL: str = Field(
        default="http://n8n:5678/webhook/itinerary-agent-staging",  # Change for this in production: https://voya-itinerary.app.n8n.cloud/webhook/itinerary-agent
        description="n8n webhook URL for itinerary agent",
    )
    N8N_WEBHOOK_SECRET: str = Field(
        default="",
        description="Shared secret for n8n webhook authentication",
    )
    N8N_CAPABILITIES_API_KEY: str | None = Field(
        default=None,
        description="API key for n8n to call Capabilities API endpoints. "
        "Used by /api/itinerary/capabilities/* endpoints for authentication.",
    )

    # ================== LANGGRAPH AI AGENTS ==================
    # Note: USE_LANGGRAPH_FLIGHTS, USE_LANGGRAPH_HOTELS, USE_LANGGRAPH_ITINERARY,
    # and USE_LANGGRAPH_ROUTER flags were removed. LangGraph is now the only code
    # path for flights, hotels, and itinerary. The env vars may still exist in
    # Terraform/ECS but are ignored (extra="ignore").
    VOYA_FEATURE_FLAG_USE_LANGGRAPH_ITINERARY_V2: bool = Field(
        default=False,
        description="Use V2 LangGraph ReAct agent for itinerary planning instead of V1 supervisor. "
        "When enabled, CREATE_ITINERARY intent is routed to the dynamic itinerary agent. "
        "Requires LangGraph itinerary to be active (now always true).",
    )
    VOYA_FEATURE_FLAG_USE_V2_SUPERVISOR: bool = Field(
        default=False,
        description="Use V2 Supervisor for all message routing. "
        "When enabled, bypasses IntentRecognizer and V1 router, routing all messages "
        "through the V2 Supervisor that classifies intent and delegates to sub-agents.",
    )
    VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS: bool = Field(
        default=False,
        description="Use FlightLogic API for airport search and resolution instead of mwgg/Airports. "
        "When enabled, airport endpoints use FlightLogic's /airport_list endpoint which provides "
        "commercial airports only (excluding private/military airports).",
    )

    MULTICITY_PARALLEL_SEARCH: bool = Field(
        default=True,
        description="When True, Circle (multi-city) search uses N parallel OneWay FlightLogic calls "
        "with per-leg session_ids. When False, uses a single legacy Circle request (combined results). "
        "Rollback: set MULTICITY_PARALLEL_SEARCH=false in the environment.",
    )
    FLIGHT_SEARCH_CONCURRENT_REVALIDATION: bool = Field(
        default=False,
        description=(
            "When True, after flight search (and filters), up to revalidate_flights_count "
            "fares are revalidated against FlightLogic in parallel (asyncio.gather) and "
            "invalid fares are removed from results. When False, that post-search step is "
            "skipped entirely (no revalidate API calls, no removal). Default False for "
            "local and non-prod; production sets True via Terraform. Rollback: set to 'false'."
        ),
    )

    # ================== CHAT FEEDBACK FEATURE ==================
    VOYA_FEATURE_FLAG_CHAT_FEEDBACK: bool = Field(
        default=False,
        description="Enable thumbs up/down feedback buttons in chat UI. "
        "When enabled, frontend shows feedback buttons on AI responses for user rating.",
    )

    # ================== PUBLIC (GUEST) LANDING CHAT ==================
    VOYA_FEATURE_FLAG_PUBLIC_CHAT: bool = Field(
        default=True,
        description="Enable unauthenticated chat on the public landing page via POST /api/public/chat/message. "
        "Set to false to disable (opt-out).",
    )
    PUBLIC_CHAT_MESSAGES_PER_MINUTE: int = Field(
        default=security_constants.PUBLIC_CHAT_MESSAGES_PER_MINUTE,
        description="Max guest chat messages per client IP per 60s (sliding window). Override for testing.",
    )
    PUBLIC_CHAT_MESSAGES_PER_SESSION: int = Field(
        default=security_constants.PUBLIC_CHAT_MESSAGES_PER_SESSION,
        description="Max guest chat messages per X-Public-Chat-Session (lifetime, in-process). Override for testing.",
    )
    TRUST_X_FORWARDED_FOR: bool = Field(
        default=False,
        description="When True, use the rightmost X-Forwarded-For address for client IP (e.g. behind ALB). "
        "When False, use the direct connection address only — required when the API is exposed without a "
        "trusted proxy, otherwise clients can spoof X-Forwarded-For and bypass per-IP limits.",
    )
    PLACES_SESSION_TOKEN_SECRET: str = Field(
        default="",
        description="HMAC key for guest Places photo session JWT. Empty uses SECRET_KEY + '_places' (set explicitly in production).",
    )
    PLACES_SESSION_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        ge=1,
        le=7 * 24 * 60,
        description="Lifetime for X-Places-Session-Token JWT (minutes).",
    )

    # ================== SENTRY ERROR TRACKING ==================
    SENTRY_DSN: str | None = Field(
        default=None,
        description="Sentry DSN for error tracking. Leave empty to disable Sentry.",
    )
    SENTRY_TRACES_SAMPLE_RATE: float = Field(
        default=0.1,
        description="Sentry performance monitoring sample rate (0.0 to 1.0). "
        "Use 1.0 for development, 0.1 for production.",
    )
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(
        default=0.1,
        description="Sentry profiling sample rate (0.0 to 1.0).",
    )

    # ================== CHAT STREAMING (Issue #1117 / #1053 Phase 3 O2) ==================
    CHAT_STREAMING_ENABLED: bool = Field(
        default=True,
        description=(
            "Enable Server-Sent-Events streaming for POST /chat/message/stream. "
            "When False the endpoint returns 404 so the frontend falls back to "
            "the non-streaming POST /chat/message. Default flipped to True so "
            "staging/prod get skeleton-streaming without explicit env setup; "
            "the env var is still the rollback escape hatch if an environment "
            "needs to opt out."
        ),
    )

    # ================== TWO-STAGE ITINERARY (#1053 Phase 4 O1) ==================
    TWO_STAGE_ITINERARY_ENABLED: bool = Field(
        default=True,
        description=(
            "Enable Skeleton-of-Thought two-stage itinerary generation. When True, "
            "_generate_itinerary_with_llm splits the single ~25-45 s LLM call into "
            "(1) a fast stage-1 skeleton call producing day titles + budget + "
            "experiences, then (2) N parallel stage-2 calls each filling activities "
            "for one day. Cuts the LLM portion of the cold-turn budget from "
            "~25-45 s to ~10 s p50 with no per-token cost change on gpt-5.4-mini. "
            "Default flipped to True so staging/prod get the speedup without "
            "explicit env setup; flag-gated so the single-call path stays the "
            "rollback escape hatch."
        ),
    )
    TWO_STAGE_PARALLEL_LIMIT: int = Field(
        default=10,
        description=(
            "Max chunks (= concurrent stage-2 LLM calls) per itinerary turn. "
            "With the chunk-based Stage 2 (#1140) all N chunks fire in ONE "
            "asyncio.gather batch regardless of trip length, so this controls "
            "chunk granularity (quality) not latency. "
            "At 10: 30-day trip → 10 chunks of 3 days each (good coherence); "
            "7-day trip → 7 chunks of 1 day each (unchanged). "
            "Raise to 14-15 for even finer chunks on long trips (Tier 2+ only). "
            "Safe floor is 7 for conservative Tier 1 orgs."
        ),
    )

    # ================== LANGFUSE OBSERVABILITY ==================
    LANGFUSE_ENABLED: bool = Field(
        default=False,
        description="Enable Langfuse LLM observability for debugging LangGraph agents.",
    )
    LANGFUSE_SECRET_KEY: str | None = Field(
        default=None,
        description="Langfuse secret key for authentication.",
    )
    LANGFUSE_PUBLIC_KEY: str | None = Field(
        default=None,
        description="Langfuse public key for authentication.",
    )
    LANGFUSE_BASE_URL: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse API base URL (cloud or self-hosted).",
    )
    LANGFUSE_PROMPT_LABEL: str = Field(
        default="production",
        description="Langfuse prompt label to fetch (production, staging, latest, etc.).",
    )

    # ================== EXTERNAL APIS - PAYMENT ==================
    STRIPE_SECRET_KEY: str | None = Field(
        default=None,
        description="Stripe secret key",
    )
    STRIPE_PUBLISHABLE_KEY: str | None = Field(
        default=None,
        description="Stripe publishable key",
    )
    STRIPE_WEBHOOK_SECRET: str | None = Field(
        default=None,
        description="Stripe webhook signing secret for verifying webhook events",
    )
    STRIPE_USE_CONNECT_TRANSFERS: bool = Field(
        default=True,
        description="Enable Stripe Connect transfers to supplier accounts. "
        "Set to False for testing when Connect account lacks transfer capability.",
    )
    FLIGHTLOGIC_STRIPE_ACCOUNT_ID: str | None = Field(
        default=None,
        description="FlightLogic's Stripe Connect account ID for receiving payments. "
        "If not set, uses VOYA_STRIPE_TEST_CONNECT_ACCOUNT_ID from constants.",
    )

    # Payment provider selection (stripe or revolut)
    PAYMENT_PROVIDER: str = Field(
        default="stripe",
        description="Payment provider to use: 'stripe' or 'revolut'. Defaults to 'stripe' for backward compatibility.",
    )

    # Revolut Merchant API configuration
    REVOLUT_API_BASE_URL: str = Field(
        default="https://sandbox-merchant.revolut.com/api",
        description="Revolut Merchant API base URL. "
        "Defaults to sandbox. Override with: "
        "https://sandbox-merchant.revolut.com/api (sandbox) "
        "or https://merchant.revolut.com/api (production). "
        "Auto-configured based on ENVIRONMENT if not explicitly set.",
    )
    REVOLUT_API_KEY: str | None = Field(
        default=None,
        description="Revolut Merchant API key (secret key)",
    )
    REVOLUT_PUBLIC_KEY: str | None = Field(
        default=None,
        description="Revolut public key for frontend integration",
    )
    REVOLUT_WEBHOOK_SECRET: str | None = Field(
        default=None,
        description="Revolut webhook signing secret for verifying webhook events",
    )
    REVOLUT_MERCHANT_ID: str | None = Field(
        default=None,
        description="Revolut merchant account ID for supplier payouts",
    )
    REVOLUT_ENVIRONMENT: str = Field(
        default="sandbox",
        description="Revolut environment: 'sandbox' or 'prod'",
    )

    # ================== ACTIVECAMPAIGN CONFIGURATION ==============
    ACTIVECAMPAIGN_API_URL: str | None = Field(
        default=None,
        description=(
            "ActiveCampaign account-specific base URL "
            "(e.g. https://youraccount.api-ac.com). Leave unset to disable."
        ),
    )
    ACTIVECAMPAIGN_API_KEY: str | None = Field(
        default=None,
        description="ActiveCampaign API key used in the Api-Token header.",
    )

    # ================== EMAIL CONFIGURATION ======================
    SENDGRID_API_KEY: str | None = Field(
        default=None,
        description="SendGrid API key",
    )
    SENDGRID_FROM_EMAIL: str = Field(
        default="noreply@myvoya.ai",
        description='Default "from" address for SendGrid',
    )

    # ================== EMAIL PROVIDER SELECTION ==================
    USE_MAILHOG: bool = Field(
        default=False,
        description="Use MailHog instead of SendGrid for local email testing - defaults to True in development",
    )
    MAILHOG_HOST: str = Field(
        default="mailhog", description="MailHog SMTP server hostname"
    )
    MAILHOG_PORT: int = Field(default=1025, description="MailHog SMTP server port")
    EMAIL_FOOTER_TEXT: str = (
        "© 2025 Voya AI, Inc. All rights reserved."  # Can be overridden in .env
    )
    DEV_EMAIL_RECIPIENT: str | None = None  # TO BE UPDATED
    API_TESTER_BASE_URL: str | None = None  # TO BE UPDATED

    # ================== RATE LIMITING & CACHING ==================
    RATE_LIMIT_ENABLED: bool = Field(
        default=False, description="Enable/Disable rate limiting"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=100,  # seconds
        description="Limit per minute",
    )
    CACHE_TTL_SECONDS: int = Field(
        default=60,  # seconds
        description="Cache TTL per second",
    )

    # ================== LOGGING ==================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_FILE_PATH: str | None = "logs/app.log"  # Set to None to disable file logging
    LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB per log file
    LOG_FILE_BACKUP_COUNT: int = 5  # Keep 5 backup files
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # ================== PDF GENERATION ==================
    PDF_OUTPUT_DIR: str = Field(
        default="logs/pdfs", description="Directory for storing generated PDF files"
    )
    PDF_CLEAR_ON_STARTUP: bool = Field(
        default=True,
        description="Clear PDF directory on server startup (development/testing)",
    )

    # ================== COMPUTED PROPERTIES ==================
    @property
    def frontend_url(self) -> str:
        """Get frontend URL."""
        return self.FRONTEND_URL

    # ================== VALIDATORS ==================
    @classmethod
    @field_validator("ENVIRONMENT", mode="before")
    def validate_app_environment(cls, v: str | None) -> str | None:
        """Validate and normalize the ENVIRONMENT field."""
        if v is None:
            return v

        # case‑insensitive check against the allowed environments
        v_lower = v.lower()
        allowed = {"development", "testing", "staging", "production"}

        if v_lower not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {sorted(allowed)}, got '{v}'")
        return v_lower

    @classmethod
    @field_validator("REVOLUT_ENVIRONMENT", mode="before")
    def validate_revolut_environment(cls, v: str | None) -> str:
        """Normalize and validate REVOLUT_ENVIRONMENT value."""
        if v is None:
            return "sandbox"
        v_lower = str(v).lower().strip()
        if v_lower not in ("sandbox", "prod"):
            raise ValueError(
                f"REVOLUT_ENVIRONMENT must be 'sandbox' or 'prod', got: {v}"
            )
        return v_lower

    @classmethod
    @field_validator("LOG_LEVEL")
    def validate_log_level(cls, v: str | None) -> str | None:
        """Validate LOG_LEVEL is a valid Python logging level."""
        if v is None:
            return v
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got '{v}'")
        return v.upper()

    @model_validator(mode="after")
    def set_mailhog_default(self) -> "Settings":
        """Set USE_MAILHOG based on environment if not explicitly set."""
        # If USE_MAILHOG was not explicitly provided, set based on environment
        # Default True for development, False for production
        if not hasattr(self, "_use_mailhog_set"):
            if self.ENVIRONMENT.lower() == "development":
                self.USE_MAILHOG = True
            self._use_mailhog_set = True  # Flag to prevent re-running
        return self

    @model_validator(mode="after")
    def warn_places_session_secret_in_production(self) -> "Settings":
        """Recommend an explicit Places session signing key in production."""
        if (
            self.ENVIRONMENT.lower() == "production"
            and not self.PLACES_SESSION_TOKEN_SECRET
        ):
            logging.getLogger(__name__).warning(
                "PLACES_SESSION_TOKEN_SECRET is not set; deriving signing key from SECRET_KEY. "
                "Set PLACES_SESSION_TOKEN_SECRET explicitly in production for independent rotation."
            )
        return self

    @classmethod
    @field_validator("MONGODB_URI")
    def validate_mongodb_uri(cls, v: str) -> str:
        """Validate MongoDB connection string format."""
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError(
                "Invalid MongoDB URL format - must start with mongodb:// or mongodb+srv://"
            )
        return v

    @classmethod
    @field_validator("FLIGHTLOGIC_API_URL")
    def validate_flightlogic_url(cls, v: str | None) -> str | None:
        """Validate FlightLogic API URL if provided (deprecated)."""
        if v:
            import warnings

            warnings.warn(
                "FLIGHTLOGIC_API_URL is deprecated. Use FLIGHTLOGIC_FLIGHTS_API_BASE_URL "
                "and FLIGHTLOGIC_HOTELS_API_BASE_URL instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            if not v.startswith(("http://", "https://")):
                raise ValueError(
                    "FlightLogic API URL must start with http:// or https://"
                )
        return v

    @classmethod
    @field_validator(
        "FLIGHTLOGIC_FLIGHTS_API_BASE_URL", "FLIGHTLOGIC_HOTELS_API_BASE_URL"
    )
    def validate_flightlogic_base_urls(cls, v: str) -> str:
        """Validate FlightLogic base URLs."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(
                "FlightLogic base URLs must start with http:// or https://"
            )
        return v

    @classmethod
    @field_validator("REVOLUT_API_BASE_URL")
    def validate_revolut_api_base_url(cls, v: str) -> str:
        """Validate Revolut API base URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("REVOLUT_API_BASE_URL must start with http:// or https://")
        return v

    @classmethod
    @field_validator("ACTIVECAMPAIGN_API_URL")
    def validate_activecampaign_api_url(cls, v: str | None) -> str | None:
        """Validate ActiveCampaign API URL if set (integration is opt-in)."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError(
                "ACTIVECAMPAIGN_API_URL must start with http:// or https://"
            )
        return v

    @classmethod
    @field_validator("FRONTEND_URL", mode="after")
    def validate_frontend_url(cls, v: str | None) -> str | None:
        """Validate frontend URL if provided - allow HTTP for localhost/development."""
        if v is None:
            return v

        if not v.startswith(("http://", "https://")):
            raise ValueError("Frontend URL must start with http:// or https://")

        # Allow HTTP only for localhost/development

        if v.startswith("http://") and not any(
            host in v for host in ["localhost", "127.0.0.1"]
        ):
            raise ValueError(
                "HTTP URLs are only allowed for localhost/development - use HTTPS for production"
            )

        return v

    @classmethod
    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v: Any) -> str | list[str]:
        """Parse and validate CORS origins from string or list."""
        # Keep the value as-is for further processing
        # The actual parsing happens in the after validator
        if not v:
            return []
        return v

    @classmethod
    @field_validator("CORS_ORIGINS", mode="after")
    def validate_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Validate CORS origins after parsing."""
        # Convert string to list if needed
        if isinstance(v, str):
            if not v.strip():  # Handle empty strings
                return [
                    "http://localhost:3000",
                    "http://localhost:3001",
                    "http://localhost:5000",
                    "https://app.myvoya.ai",
                    "https://www.myvoya.ai",
                ]
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        else:
            origins = v if v else []

        if origins:  # Only validate if there are origins
            for origin in origins:
                if not origin.startswith(("http://", "https://", "*")):
                    raise ValueError(
                        f"CORS origin must start with http://, https://, or be '*': {origin}"
                    )

                # Allow HTTP only for localhost/development
                if origin.startswith("http://") and not any(
                    host in origin for host in ["localhost", "127.0.0.1"]
                ):
                    raise ValueError(
                        f"HTTP CORS origins are only allowed for localhost/development: {origin}"
                    )

        return origins

    @classmethod
    @field_validator("FLIGHTLOGIC_ACCESS_TYPE")
    def validate_flightlogic_access_type(cls, v: str | None) -> str | None:
        """Validate FlightLogic access type if provided."""
        valid_types = ["Test", "Production"]
        if v is not None and v not in valid_types:
            raise ValueError(f"FLIGHTLOGIC_ACCESS_TYPE must be one of {valid_types}")
        return v

    @field_validator("PAYMENT_PROVIDER")
    def validate_payment_provider(cls, v: str) -> str:
        """Validate payment provider is either 'stripe' or 'revolut'."""
        valid_providers = ["stripe", "revolut"]
        v_lower = v.lower() if v else "stripe"
        if v_lower not in valid_providers:
            raise ValueError(
                f"PAYMENT_PROVIDER must be one of {valid_providers}, got '{v}'"
            )
        return v_lower

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate critical settings for production environment."""
        if self.ENVIRONMENT == "production":
            # Security checks
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Production requires a secure SECRET_KEY of at least 32 characters"
                )
            if self.DEBUG:
                print("WARNING: DEBUG is True in production environment")

            # API keys check (warning only - logged, not raised)
            if not self.FLIGHTLOGIC_API_KEY:
                print("WARNING: FlightLogic API key not configured for production")
            if not self.STRIPE_SECRET_KEY:
                print("WARNING: Stripe API key not configured for production")
            if not self.SENDGRID_API_KEY:
                print(
                    "WARNING: SendGrid API key not configured for production - emails will not be delivered"
                )
            if not self.PASSENGER_ENCRYPTION_KEY:
                print(
                    "WARNING: PASSENGER_ENCRYPTION_KEY not configured for production - passenger storage will fail at runtime"
                )

        return self

    @model_validator(mode="after")
    def auto_configure_settings(self) -> "Settings":
        """Auto-configure settings based on environment."""
        # ENVIRONMENT must be set in .env
        if self.ENVIRONMENT is None:
            raise ValueError(
                "ENVIRONMENT must be set in .env file (development, staging, or production)"
            )

        # HOST and PORT must be set in .env
        if self.HOST is None:
            raise ValueError("HOST must be set in .env file")
        if self.PORT is None:
            raise ValueError("PORT must be set in .env file")

        # LOG_LEVEL must be set in .env
        if self.LOG_LEVEL is None:
            raise ValueError("LOG_LEVEL must be set in .env file")

        # FRONTEND_URL must be set in .env
        if self.FRONTEND_URL is None:
            raise ValueError("FRONTEND_URL must be set in .env file")

        # CORS_ORIGINS is already parsed by field_validator

        # FLIGHTLOGIC_ACCESS_TYPE must be set in .env
        if self.FLIGHTLOGIC_ACCESS_TYPE is None:
            raise ValueError(
                "FLIGHTLOGIC_ACCESS_TYPE must be set in .env file (Test or Production)"
            )

        # SENDGRID_FROM_EMAIL must be set in .env
        if self.SENDGRID_FROM_EMAIL is None:
            raise ValueError("SENDGRID_FROM_EMAIL must be set in .env file")

        # Set REVOLUT_API_BASE_URL based on environment if not explicitly set
        # Only override if not explicitly set via environment variable
        if (
            "REVOLUT_API_BASE_URL" not in self.model_fields_set
            and self.ENVIRONMENT.lower() == "production"
        ):
            self.REVOLUT_API_BASE_URL = "https://merchant.revolut.com/api"
        # else: keep default sandbox URL

        return self

    @model_validator(mode="after")
    def validate_api_dependencies(self) -> "Settings":
        """Validate API configuration completeness."""
        # FlightLogic validation - use new fields, fallback to deprecated
        if self.FLIGHTLOGIC_API_KEY and not all(
            [
                self.FLIGHTLOGIC_FLIGHTS_API_BASE_URL
                or self.FLIGHTLOGIC_API_URL,  # Allow backward compatibility
                self.FLIGHTLOGIC_USER_ID,
                self.FLIGHTLOGIC_PASSWORD,
            ]
        ):
            raise ValueError(
                "FlightLogic requires FLIGHTS_API_BASE_URL (or deprecated API_URL), USER_ID, and PASSWORD when API_KEY is set"
            )

        # Stripe validation
        if self.STRIPE_SECRET_KEY and not self.STRIPE_PUBLISHABLE_KEY:
            print("WARNING: Stripe publishable key not set")

        return self


# Create settings instance - BaseSettings automatically loads from .env file
# PyCharm may show warnings about missing required fields - these are loaded from .env
# noinspection PyTypeChecker
settings: Settings = Settings()
