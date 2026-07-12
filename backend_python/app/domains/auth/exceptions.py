"""Authentication domain exceptions.

All custom exceptions for authentication operations with proper error handling.
"""


class AuthDomainError(Exception):
    """Base exception for all auth domain errors."""

    def __init__(
        self, message: str = "Authentication error occurred", code: str | None = None
    ) -> None:
        self.message = message
        self.code = code or "AUTH_ERROR"
        super().__init__(self.message)


# ==============================================================================
# REGISTRATION EXCEPTIONS
# ==============================================================================


class RegistrationError(AuthDomainError):
    """Raised when registration fails."""

    def __init__(self, reason: str | None = None) -> None:
        message = f"Registration failed: {reason}" if reason else "Registration failed"
        super().__init__(message, "REGISTRATION_ERROR")
        self.reason = reason


class EmailNotVerifiedError(AuthDomainError):
    """Raised when action requires email verification."""

    def __init__(self, email: str | None = None) -> None:
        message = (
            f"Email {email} is not verified" if email else "Email verification required"
        )
        super().__init__(message, "EMAIL_NOT_VERIFIED")
        self.email = email


# ==============================================================================
# AUTHENTICATION EXCEPTIONS
# ==============================================================================


class InvalidCredentialsError(AuthDomainError):
    """Raised when email/password combination is invalid."""

    def __init__(self, email: str | None = None) -> None:
        message = (
            f"Invalid credentials for {email}" if email else "Invalid email or password"
        )
        super().__init__(message, "INVALID_CREDENTIALS")
        self.email = email


class GoogleAuthError(AuthDomainError):
    """Raised when Google authentication fails."""

    def __init__(self, reason: str | None = None) -> None:
        message = (
            f"Google authentication failed: {reason}"
            if reason
            else "Google authentication failed"
        )
        super().__init__(message, "GOOGLE_AUTH_ERROR")
        self.reason = reason


# ==============================================================================
# TOKEN & SESSION EXCEPTIONS
# ==============================================================================


class InvalidTokenError(AuthDomainError):
    """Raised when a token is invalid or malformed."""

    def __init__(
        self, token_type: str | None = None, reason: str | None = None
    ) -> None:
        if token_type and reason:
            message = f"Invalid {token_type} token: {reason}"
        elif token_type:
            message = f"Invalid {token_type} token"
        else:
            message = "Invalid or malformed token"
        super().__init__(message, "INVALID_TOKEN")
        self.token_type = token_type
        self.reason = reason


class TokenExpiredError(AuthDomainError):
    """Raised when a token has expired."""

    def __init__(self, token_type: str | None = None) -> None:
        message = (
            f"{token_type} token has expired" if token_type else "Token has expired"
        )
        super().__init__(message, "TOKEN_EXPIRED")
        self.token_type = token_type


class RefreshTokenError(AuthDomainError):
    """Raised when refresh token operation fails."""

    def __init__(self, reason: str | None = None) -> None:
        message = (
            f"Failed to refresh token: {reason}"
            if reason
            else "Failed to refresh token"
        )
        super().__init__(message, "REFRESH_TOKEN_ERROR")
        self.reason = reason


class SessionNotFoundError(AuthDomainError):
    """Raised when session is not found."""

    def __init__(self, session_id: str | None = None) -> None:
        message = (
            f"Session {session_id} not found" if session_id else "Session not found"
        )
        super().__init__(message, "SESSION_NOT_FOUND")
        self.session_id = session_id


# ==============================================================================
# PASSWORD EXCEPTIONS
# ==============================================================================


class InvalidPasswordError(AuthDomainError):
    """Raised when password doesn't meet requirements."""

    def __init__(self, reason: str | None = None) -> None:
        message = (
            f"Invalid password: {reason}"
            if reason
            else "Password does not meet requirements"
        )
        super().__init__(message, "INVALID_PASSWORD")
        self.reason = reason


class PasswordResetError(AuthDomainError):
    """Raised when password reset fails."""

    def __init__(self, reason: str | None = None) -> None:
        message = (
            f"Password reset failed: {reason}" if reason else "Password reset failed"
        )
        super().__init__(message, "PASSWORD_RESET_ERROR")
        self.reason = reason


# ==============================================================================
# SECURITY EXCEPTIONS
# ==============================================================================


class TooManyAttemptsError(AuthDomainError):
    """Raised when too many failed login attempts are made."""

    def __init__(self, locked_until: str | None = None) -> None:
        if locked_until:
            message = f"Account locked due to too many failed attempts. Try again after {locked_until}"
        else:
            message = "Too many failed login attempts"
        super().__init__(message, "TOO_MANY_ATTEMPTS")
        self.locked_until = locked_until


class AccountLockedError(AuthDomainError):
    """Raised when attempting to login to a locked account."""

    def __init__(
        self, reason: str | None = None, locked_until: str | None = None
    ) -> None:
        if locked_until:
            message = f"Account is locked until {locked_until}"
        elif reason:
            message = f"Account is locked: {reason}"
        else:
            message = "Account is locked"
        super().__init__(message, "ACCOUNT_LOCKED")
        self.reason = reason
        self.locked_until = locked_until
