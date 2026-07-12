from typing import Any

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator
from pydantic_settings import SettingsConfigDict

from app.core import security_constants


class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings for env-management."""

    # ================== APPLICATION CORE ==================
    APP_NAME: str = Field(default="Voya API")
    VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development")  # development, staging, production
    DEBUG: bool = Field(default=False)  # overridden by ENV
    HOST: str = Field(default="0.0.0.0")  # Docker/development
    PORT: int = Field(default=8000)

    # ================== SECURITY ==================
    SECRET_KEY: str = Field(
        default="dev-secret-key-please-change-in-production",
        description="JWT signing key - override in prod",
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
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5000",
        ]
    )

    FRONTEND_URL: str = Field(default="http://localhost:3000")
    PRODUCTION_FRONTEND_URL: str = Field(default="https://www.myvoya.ai")
    STAGING_FRONTEND_URL: str = Field(default="https://staging.myvoya.ai")

    model_config = SettingsConfigDict(
        env_file=".env",  # load .env during development
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ================== EXTERNAL APIS - AI ==================
    GOOGLE_API_KEY: str | None = Field(
        default=None,
        description="Key for Google AI services",
    )
    GEMINI_API_KEY: str | None = Field(
        default=None,
        description="Google Gemini API key",
    )
    GOOGLE_OAUTH_CLIENT_ID: str | None = Field(
        default=None,
        description="Google Sign-In client ID",
    )

    # ================== EXTERNAL APIS - FLIGHTLOGIC ==================
    FLIGHTLOGIC_API_URL: str | None = Field(
        default=None,
        description="Base URL for FlightLogic API",
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
        description="‘Test’ or ‘Production’ access",
    )
    FLIGHTLOGIC_IP_ADDRESS: str | None = Field(
        default=None,
        description="IP address of the FlightLogic instance",
    )

    # ================== EXTERNAL APIS - PAYMENT & EMAIL ==================
    STRIPE_SECRET_KEY: str | None = Field(
        default=None,
        description="Stripe secret key",
    )
    STRIPE_PUBLISHABLE_KEY: str | None = Field(
        default=None,
        description="Stripe publishable key",
    )
    SENDGRID_API_KEY: str | None = Field(
        default=None,
        description="SendGrid API key",
    )
    SENDGRID_FROM_EMAIL: str = Field(
        default="noreply@voya.com",
        description="Default 'from' address for SendGrid",
    )

    # ================== RATE LIMITING & CACHING ==================
    RATE_LIMIT_ENABLED: bool = False  # Disabled by default for development
    RATE_LIMIT_PER_MINUTE: int = 60
    CACHE_TTL_SECONDS: int = 3600  # 1 hour default

    # ================== LOGGING ==================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_FILE_PATH: str | None = "logs/app.log"  # Set to None to disable file logging
    LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB per log file
    LOG_FILE_BACKUP_COUNT: int = 5  # Keep 5 backup files
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    # ================== COMPUTED PROPERTIES ==================
    @property
    def frontend_url(self) -> str:
        """Get frontend URL based on environment."""
        if self.ENVIRONMENT == "production":
            return self.PRODUCTION_FRONTEND_URL
        if self.ENVIRONMENT == "staging":
            return self.STAGING_FRONTEND_URL
        return self.FRONTEND_URL

    # ================== VALIDATORS ==================
    @field_validator("DEBUG", mode="before")
    @classmethod
    def set_debug_default(cls, v: Any) -> bool:
        """Set DEBUG based on environment if not explicitly provided."""
        if v is None:
            # For development environment, default to True
            return True
        return bool(v)

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def set_log_level_default(cls, v: Any) -> str:
        """Set LOG_LEVEL based on environment if not explicitly provided."""
        if v is None:
            return "INFO"
        return str(v)

    @field_validator("MONGODB_URI")
    @classmethod
    def validate_mongodb_uri(cls, v: str) -> str:
        """Validate MongoDB connection string format."""
        if not v.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError(
                "Invalid MongoDB URL format - must start with mongodb:// or mongodb+srv://"
            )
        return v

    @field_validator("FLIGHTLOGIC_API_URL")
    @classmethod
    def validate_flightlogic_url(cls, v: str | None) -> str | None:
        """Validate FlightLogic API URL if provided."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("FlightLogic API URL must start with http:// or https://")
        return v

    @field_validator(
        "FRONTEND_URL", "PRODUCTION_FRONTEND_URL", "STAGING_FRONTEND_URL", mode="after"
    )
    @classmethod
    def validate_frontend_urls(cls, v: str) -> str:
        """Validate frontend URLs - allow HTTP for localhost/development."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Frontend URL must start with http:// or https://")

        # Allow HTTP only for localhost/development
        if v.startswith("http://") and not any(
            host in v for host in ["localhost", "127.0.0.1", "0.0.0.0"]
        ):
            raise ValueError(
                "HTTP URLs are only allowed for localhost/development - use HTTPS for production"
            )

        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse and validate CORS origins from string or list."""
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",")]
        else:
            origins = v

        # Validate each origin
        for origin in origins:
            if not origin.startswith(("http://", "https://", "*")):
                raise ValueError(
                    f"CORS origin must start with http://, https://, or be '*': {origin}"
                )

            # Allow HTTP only for localhost/development
            if origin.startswith("http://") and not any(
                host in origin for host in ["localhost", "127.0.0.1", "0.0.0.0"]
            ):
                raise ValueError(
                    f"HTTP CORS origins are only allowed for localhost/development: {origin}"
                )

        return origins

    @field_validator("FLIGHTLOGIC_ACCESS_TYPE")
    @classmethod
    def validate_access_type(cls, v: str) -> str:
        """Validate FlightLogic access type."""
        if v not in ["Test", "Production"]:
            raise ValueError("FLIGHTLOGIC_ACCESS_TYPE must be 'Test' or 'Production'")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Validate critical settings for production environment."""
        if self.ENVIRONMENT == "production":
            # Security checks
            if self.SECRET_KEY == "dev-secret-key-please-change-in-production":  # noqa: S105
                raise ValueError("Production requires a secure SECRET_KEY")
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")

            # API keys check (warning only - logged, not raised)
            if not self.FLIGHTLOGIC_API_KEY:
                print("WARNING: FlightLogic API key not configured for production")
            if not self.STRIPE_SECRET_KEY:
                print("WARNING: Stripe API key not configured for production")

        return self

    @model_validator(mode="after")
    def validate_api_dependencies(self) -> "Settings":
        """Validate API configuration completeness."""
        # FlightLogic validation
        if self.FLIGHTLOGIC_API_KEY and not all(
            [
                self.FLIGHTLOGIC_API_URL,
                self.FLIGHTLOGIC_USER_ID,
                self.FLIGHTLOGIC_PASSWORD,
            ]
        ):
            raise ValueError(
                "FlightLogic requires API_URL, USER_ID, and PASSWORD when API_KEY is set"
            )

        # Stripe validation
        if self.STRIPE_SECRET_KEY and not self.STRIPE_PUBLISHABLE_KEY:
            print("WARNING: Stripe publishable key not set")

        return self

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )


settings = Settings()
