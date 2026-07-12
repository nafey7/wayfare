"""Authentication schemas for API requests and responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, ValidationInfo, field_validator

from app.domains.common import EmailStr, datetime, now_utc, timedelta
from app.shared.schemas import StrictModel

if TYPE_CHECKING:
    from app.domains.user.schemas import UserResponse

# ==============================================================================
# REGISTRATION FLOW
# ==============================================================================


class EmailCheckRequest(StrictModel):
    """Check if email exists and user status."""

    email: EmailStr


class EmailCheckResponse(StrictModel):
    """Response for email status check."""

    exists: bool
    verified: bool | None = None
    message: str


class RegisterRequest(StrictModel):
    """Register new user."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)


class CompleteRegistrationRequest(StrictModel):
    """Complete registration with password."""

    token: str
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @classmethod
    @field_validator("confirm_password")
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """Validate that password and confirm_password match."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


# ==============================================================================
# LOGIN/AUTHENTICATION
# ==============================================================================


class LoginRequest(StrictModel):
    """Login with email and password."""

    email: EmailStr
    password: str
    fingerprint: str | None = None


class GoogleAuthRequest(StrictModel):
    """Google OAuth authentication."""

    id_token: str
    fingerprint: str | None = None


# ==============================================================================
# SESSION & TOKEN MANAGEMENT
# ==============================================================================


class RefreshTokenRequest(StrictModel):
    """Refresh access token."""

    refresh_token: str


class TokenResponse(StrictModel):
    """Token response with access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth2 standard token type, not a password
    expires_in: int = 1800  # 30 minutes


class SessionCreate(StrictModel):
    """Schema for creating a new session."""

    user_id: str
    fingerprint: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    refresh_token: str
    expires_at: datetime


class SessionResponse(StrictModel):
    """User session information."""

    id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    is_current: bool = False  # Indicates if this is the current session

    @classmethod
    def from_model(cls, session: Any, is_current: bool = False) -> SessionResponse:
        """Create from database session model."""
        # Get expires_at from expires_at field, fallback to access_token_expires
        expires_at = getattr(session, "expires_at", None)
        if expires_at is None:
            expires_at = getattr(session, "access_token_expires", None)

        if expires_at is None:
            expires_at = now_utc() + timedelta(days=1)

        return cls(
            id=str(session.id) if session.id else "",
            user_id=str(session.user_id) if session.user_id else "",
            created_at=getattr(session, "created_at", now_utc()),
            last_activity=getattr(session, "last_activity", now_utc()),
            expires_at=expires_at,
            ip_address=getattr(session, "ip_address", None),
            user_agent=getattr(session, "user_agent", None),
            is_current=is_current,
        )


class AuthResponse(StrictModel):
    """Complete authentication response."""

    user: UserResponse | dict[str, Any]
    access_token: str
    refresh_token: str
    session_id: str | None = None

    @classmethod
    def from_models(
        cls, user: Any, access_token: str, refresh_token: str, session: Any = None
    ) -> AuthResponse:
        """Create from database models."""
        from app.domains.user.schemas import UserResponse

        return cls(
            user=UserResponse.from_model(user),
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=str(session.id) if session and session.id else None,
        )

    @classmethod
    def from_dict(cls, response_dict: dict[str, Any]) -> AuthResponse:
        """Create from dictionary response (from AuthService)."""
        return cls(
            user=response_dict["user"],
            access_token=response_dict["access_token"],
            refresh_token=response_dict["refresh_token"],
            session_id=response_dict.get("session_id"),
        )


# ==============================================================================
# PASSWORD MANAGEMENT
# ==============================================================================


class ForgotPasswordRequest(StrictModel):
    """Request password reset."""

    email: EmailStr


class ValidateResetTokenRequest(StrictModel):
    """Validate password reset token."""

    token: str


class ValidateRegistrationTokenRequest(StrictModel):
    """Validate registration token (from email verification link)."""

    token: str


class ResetPasswordRequest(StrictModel):
    """Reset password with token."""

    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @classmethod
    @field_validator("confirm_password")
    def passwords_match(cls, v: str, info: ValidationInfo) -> str:
        """Validate that new_password and confirm_password match."""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class ChangePasswordRequest(StrictModel):
    """Change password for authenticated user."""

    old_password: str
    new_password: str = Field(..., min_length=8)


# Note: UserResponse is imported dynamically in the from_models method to avoid circular imports
# The TYPE_CHECKING import above is sufficient for type hints


# Rebuild AuthResponse after all forward references are available at runtime
# This is needed because AuthResponse uses UserResponse in a Union type annotation
def _rebuild_auth_models():
    """Rebuild models with forward references after imports are complete."""
    try:
        # Import UserResponse to make it available for model_rebuild
        from app.domains.user.schemas import UserResponse  # noqa: F401

        # Rebuild AuthResponse to resolve the UserResponse forward reference
        AuthResponse.model_rebuild()
    except ImportError:
        # UserResponse not yet available, will be rebuilt when needed
        pass


# Rebuild models after module initialization
_rebuild_auth_models()
