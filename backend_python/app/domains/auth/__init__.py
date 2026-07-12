"""Authentication domain package.

Clean domain-driven design for authentication.
"""

# Schemas (Data Models)
# Exceptions
from .exceptions import (
    AccountLockedError,
    AuthDomainError,
    EmailNotVerifiedError,
    GoogleAuthError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidTokenError,
    PasswordResetError,
    RefreshTokenError,
    RegistrationError,
    SessionNotFoundError,
    TokenExpiredError,
    TooManyAttemptsError,
)
from .schemas import (
    AuthResponse,
    ChangePasswordRequest,
    CompleteRegistrationRequest,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
    ValidateRegistrationTokenRequest,
    ValidateResetTokenRequest,
)

# Service (Main API)
from .service import AuthService

__all__ = [
    # Exceptions
    "AccountLockedError",
    "AuthDomainError",
    # Schemas
    "AuthResponse",
    # Service
    "AuthService",
    "ChangePasswordRequest",
    "CompleteRegistrationRequest",
    "EmailNotVerifiedError",
    "ForgotPasswordRequest",
    "GoogleAuthError",
    "GoogleAuthRequest",
    "InvalidCredentialsError",
    "InvalidPasswordError",
    "InvalidTokenError",
    "LoginRequest",
    "PasswordResetError",
    "RefreshTokenError",
    "RefreshTokenRequest",
    "RegisterRequest",
    "RegistrationError",
    "ResetPasswordRequest",
    "SessionNotFoundError",
    "SessionResponse",
    "TokenExpiredError",
    "TokenResponse",
    "TooManyAttemptsError",
    "ValidateRegistrationTokenRequest",
    "ValidateResetTokenRequest",
]
