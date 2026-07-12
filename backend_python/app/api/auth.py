"""Authentication API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domains.auth import AuthService
from app.domains.auth.exceptions import GoogleAuthError, InvalidTokenError
from app.domains.auth.schemas import (
    AuthResponse,
    CompleteRegistrationRequest,
    EmailCheckRequest,
    EmailCheckResponse,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    ValidateRegistrationTokenRequest,
    ValidateResetTokenRequest,
)
from app.domains.common import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# ==============================================================================
# PUBLIC CONFIG ENDPOINTS
# ==============================================================================


@router.get("/config/google")
async def get_google_config() -> dict[str, Any]:
    """Get Google OAuth configuration for frontend.

    Returns public configuration that frontend needs.
    Client ID is safe to expose (it's used in browser anyway).
    """
    from app.core.config import settings

    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    return {
        "client_id": client_id if client_id else None,
        "enabled": client_id is not None and len(client_id) > 0,
    }


# ==============================================================================
# REGISTRATION FLOW
# ==============================================================================


@router.post("/check-email", response_model=EmailCheckResponse)
async def check_email(request: EmailCheckRequest) -> EmailCheckResponse:
    """Check if email exists and return user status."""
    logger.info(f"🌐 [API] POST /auth/check-email called for email: {request.email}")

    from app.domains.user import UserService

    try:
        # Check if user exists
        existing_user = await UserService.get_user_public_by_email(request.email)

        if not existing_user:
            # New user
            logger.info(f"🌐 [API] Email check result: NEW USER - {request.email}")
            return EmailCheckResponse(
                exists=False, verified=None, message="New user - ready for registration"
            )

        if existing_user.email_verified:
            # Existing verified user
            logger.info(f"🌐 [API] Email check result: VERIFIED USER - {request.email}")
            return EmailCheckResponse(
                exists=True,
                verified=True,
                message="Welcome back! Please enter your password.",
            )
        # Existing unverified user - RESEND EMAIL
        logger.warning(
            f"🌐 [API] Email check result: UNVERIFIED USER - {request.email} - RESENDING EMAIL"
        )
        # Automatically resend registration email for unverified users
        from app.domains.auth.service import AuthService

        try:
            email_sent = await AuthService.send_registration_email(
                str(existing_user.id)
            )
            logger.info(
                f"🌐 [API] Resend registration email result: {email_sent} for {request.email}"
            )
        except Exception as e:
            logger.error(
                f"🌐 [API] Failed to resend registration email to {request.email}: {e}"
            )

        return EmailCheckResponse(
            exists=True,
            verified=False,
            message="Registration email resent. Please check your email to complete setup.",
        )

    except Exception as e:
        logger.error(
            f"🌐 [API] Error checking email {request.email}: {e}", exc_info=True
        )
        # Return generic response to avoid revealing system errors
        return EmailCheckResponse(
            exists=False, verified=None, message="Please try again"
        )


@router.post("/register", response_model=MessageResponse)
async def register(request: RegisterRequest) -> MessageResponse:
    """Register a new user without password - sends setup email."""
    logger.info(f"🌐 [API] POST /api/auth/register called for email: {request.email}")
    logger.info(
        f"🌐 [API] Request data: first_name='{request.first_name}', last_name='{request.last_name}'"
    )
    try:
        # Register new user without password (handles unverified users)
        # Note: register_user_passwordless already sends the email internally
        logger.info("🌐 [API] Creating AuthService instance...")
        auth_service = AuthService()

        logger.info(f"🌐 [API] Calling register_user_passwordless for: {request.email}")
        user = await auth_service.register_user_passwordless(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
        )

        logger.info(
            f"🌐 [API] register_user_passwordless completed, user_id: {user.id}"
        )

        if not user.id:
            logger.error(f"🌐 [API] ❌ User created without ID: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed - no ID assigned",
            )

    except ValueError as e:
        # For already verified users - show clear message
        if "already registered and verified" in str(e):
            logger.info(
                f"🌐 [API] Registration attempt for already verified email: {request.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already registered and verified. Please use the login option instead, or use 'Forgot Password' if you can't remember your password.",
            ) from e
        # Other errors (like database issues) should still be raised
        logger.error(f"🌐 [API] ❌ ValueError in registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            f"🌐 [API] ❌ Unexpected error in registration: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error",
        ) from e

    # For new users and unverified users
    logger.info(
        f"🌐 [API] ✅ Registration successful, returning success message for: {request.email}"
    )
    return MessageResponse(
        message="Registration initiated. Please check your email to complete setup."
    )


@router.post("/complete-registration", response_model=AuthResponse)
async def complete_registration(
    request: CompleteRegistrationRequest, req: Request
) -> AuthResponse:
    """Complete registration by setting password."""
    try:
        # Complete registration and set password
        auth_service = AuthService()
        user = await auth_service.complete_registration(
            token=request.token,
            password=request.password,
        )

        # Create session and return response using AuthService helper
        response = await auth_service.create_auth_response(
            str(user.id),
            fingerprint=None,
            ip_address=req.client.host if req.client else None,
            user_agent=req.headers.get("User-Agent"),
        )

        return AuthResponse.from_dict(response)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except InvalidTokenError as e:
        logger.warning(f"Invalid token in complete registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration token",
        ) from e


# ==============================================================================
# LOGIN & AUTHENTICATION
# ==============================================================================


@router.post("/login")
async def login(request: LoginRequest, req: Request) -> dict[str, Any]:
    """Login with email and password."""
    # First check if user exists to provide better error messages
    from app.domains.user import UserService

    existing_user = await UserService.get_user_public_by_email(request.email)

    # Authenticate user (auth_service handles verification and last login update)
    auth_service = AuthService()
    ip_address = req.client.host if req.client else None
    user = await auth_service.authenticate_user(
        request.email, request.password, ip_address=ip_address
    )
    if not user:
        # Provide specific error message if registration is not completed
        if existing_user and not existing_user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please complete your registration first. Check your email for the setup link.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create session and return response using AuthService helper
    return await auth_service.create_auth_response(
        str(user.id),
        fingerprint=request.fingerprint,
        ip_address=ip_address,
        user_agent=req.headers.get("User-Agent"),
    )


@router.post("/google/authenticate")
async def google_authenticate(
    request: Request,
    google_auth: GoogleAuthRequest,
) -> dict[str, Any]:
    """
    Google authentication with ID token.

    Uses Google Sign-In ID token for authentication.
    Creates new user account if first time, otherwise logs in existing user.

    Args:
        request: FastAPI request object for session management
        google_auth: Request containing Google ID token

    Returns:
        Authentication response with user info and tokens

    Example:
        POST /api/auth/google/authenticate
        {
            "id_token": "eyJhbGciOiJSUzI1NiIs..."
        }
    """
    try:
        # Verify ID token with Google and authenticate user
        auth_service = AuthService()
        user, is_new = await auth_service.authenticate_google_user(google_auth.id_token)

        # Create session and return response using AuthService helper
        return await auth_service.create_google_auth_response(
            user,
            is_new,
            fingerprint=google_auth.fingerprint,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )

    except GoogleAuthError as e:
        # Specific Google auth errors (like account conflicts)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except ValueError as e:
        # Invalid token format
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication token",
        ) from e


# ==============================================================================
# SESSION MANAGEMENT
# ==============================================================================


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> MessageResponse:
    """Logout current user by invalidating their session."""
    auth_service = AuthService()

    # Logout user session - this handles token decoding internally
    success = await auth_service.logout_user_session(credentials.credentials)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed - invalid or expired token",
        )

    return MessageResponse(message="Successfully logged out")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest) -> TokenResponse:
    """Refresh access token using refresh token."""
    from app.core.config import settings

    auth_service = AuthService()
    result = await auth_service.refresh_access_token(request.refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, refresh_token_ = result
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        * 60,  # Convert minutes to seconds
    )


# ==============================================================================
# PASSWORD RESET FLOW
# ==============================================================================


@router.post("/validate-registration-token")
async def validate_registration_token(
    request: ValidateRegistrationTokenRequest,
) -> dict[str, str]:
    """Validate registration token (from email verification link)."""
    try:
        auth_service = AuthService()
        await auth_service.validate_registration_token(request.token)
        return {"message": "Token is valid"}
    except (InvalidTokenError, Exception) as e:
        logger.warning(f"Invalid registration token validation attempt: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired registration token",
        ) from e


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest) -> dict[str, str]:
    """Request password reset email (for email/password users)."""
    # Always return success to avoid email enumeration
    auth_service = AuthService()
    await auth_service.send_password_reset_email(request.email)
    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/validate-reset-token")
async def validate_reset_token(request: ValidateResetTokenRequest) -> dict[str, str]:
    """Validate password reset token."""
    try:
        auth_service = AuthService()
        # Try to validate the token - this will raise an exception if invalid
        await auth_service.validate_reset_token(request.token)
        return {"message": "Token is valid"}
    except (InvalidTokenError, Exception) as e:
        logger.warning(f"Invalid reset token validation attempt: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        ) from e


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest) -> dict[str, Any]:
    """Reset password with token (for email/password users)."""
    try:
        auth_service = AuthService()
        user = await auth_service.reset_password(
            token=request.token, new_password=request.new_password
        )

        return {
            "message": "Password reset successfully",
            "user": auth_service.format_user_for_api(user),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
