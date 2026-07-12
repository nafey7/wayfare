"""Authentication dependencies for dependency injection.

Domain-layer authentication dependencies that can be used by both API routes
and domain services without creating circular imports.
"""

import logging
from collections.abc import Awaitable, Callable

import sentry_sdk
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domains.auth import AuthService
from app.domains.user.constants import UserRole
from app.domains.user.schemas import UserPublic

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer(auto_error=False)


def get_current_user_and_session(
    required: bool = True,
) -> Callable[..., Awaitable[tuple[UserPublic | None, str | None]]]:
    """Get current user and session ID from JWT token.

    This is the main authentication dependency that extracts and validates JWT tokens.
    Returns both user and session_id for maximum flexibility.

    Args:
        required: If True, raises 401 if not authenticated.
                 If False, returns (None, None) for unauthenticated requests.

    Returns:
        Dependency function that returns tuple of (User, session_id) or (None, None).

    Usage:
        # Required authentication
        user, session_id = Depends(get_current_user_and_session())

        # Optional authentication
        user, session_id = Depends(get_current_user_and_session(required=False))
    """

    async def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> tuple[UserPublic | None, str | None]:
        # No credentials provided
        if not credentials:
            logger.warning("🔐 [Auth] No credentials provided in request")
            if required:
                logger.warning(
                    "🔐 [Auth] Authentication required but not provided - returning 401"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None, None

        # Log token presence (truncated for security)
        token_preview = (
            credentials.credentials[:20] + "..."
            if len(credentials.credentials) > 20
            else credentials.credentials
        )
        logger.info(f"🔐 [Auth] Processing token: {token_preview}")

        # Verify token and get user
        auth_service = AuthService()
        user, error = await auth_service.verify_token_with_details(
            credentials.credentials
        )

        if not user:
            logger.warning(f"🔐 [Auth] Token verification failed: {error}")
            if required:
                logger.warning(
                    "🔐 [Auth] Token verification failed for required auth - returning 401"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error or "Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None, None

        logger.info(
            f"🔐 [Auth] Successfully authenticated user: {user.email} (role: {user.role})"
        )

        # Extract real client IP from X-Forwarded-For (ALB adds this)
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = (
            forwarded_for.split(",")[0].strip()
            if forwarded_for
            else request.client.host
            if request.client
            else None
        )

        # Set Sentry user context for error tracking
        sentry_sdk.set_user(
            {
                "id": user.id,
                "email": user.email,
                "username": f"{user.first_name} {user.last_name}".strip() or None,
                "ip_address": client_ip,
            }
        )

        # Get session ID from token
        session_id = await auth_service.get_session_id_from_token(
            credentials.credentials
        )
        return user, session_id

    return dependency


def get_current_user(
    required: bool = True,
) -> Callable[..., Awaitable[UserPublic | None]]:
    """Get current user from JWT token.

    Convenience wrapper that only returns the user object.
    Use this when you don't need the session ID.

    Args:
        required: If True, raises 401 if not authenticated.
                 If False, returns None for unauthenticated requests.

    Returns:
        Dependency function that returns User object or None.

    Usage:
        # Required authentication (default)
        user = Depends(get_current_user())

        # Optional authentication
        user = Depends(get_current_user(required=False))
    """

    async def dependency(
        user_and_session: tuple[UserPublic | None, str | None] = Depends(
            get_current_user_and_session(required=required)
        ),
    ) -> UserPublic | None:
        user, _ = user_and_session
        return user

    return dependency


# ============================================================
# AUTHENTICATION REQUIREMENTS
# ============================================================


async def optional_user(
    current_user: UserPublic | None = Depends(get_current_user(required=False)),
) -> UserPublic | None:
    """Get current user if authenticated, None otherwise.

    Use this for endpoints that work both authenticated and unauthenticated,
    but may provide additional features or personalization when authenticated.

    Common use cases:
    - Public chat that can be personalized when logged in
    - Public content with user-specific recommendations
    - Analytics tracking with optional user context

    Args:
        current_user: User from optional authentication check

    Returns:
        UserPublic if authenticated, None if not
    """
    return current_user


async def require_authenticated(
    current_user: UserPublic = Depends(get_current_user()),
) -> UserPublic:
    """Require user to be authenticated.

    This is essentially an alias for get_current_user() but with a clearer name
    when you explicitly want to require authentication.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        UserPublic of authenticated user

    Raises:
        HTTPException: If user is not authenticated (handled by get_current_user)
    """
    return current_user


async def require_authenticated_with_session(
    user_and_session: tuple[UserPublic, str | None] = Depends(
        get_current_user_and_session()
    ),
) -> tuple[UserPublic, str | None]:
    """Require user to be authenticated and get session info.

    Use this when you need both user and session ID (e.g., for session management).

    Args:
        user_and_session: Tuple from get_current_user_and_session dependency

    Returns:
        Tuple of (UserPublic, session_id)

    Raises:
        HTTPException: If user is not authenticated
    """
    return user_and_session


async def require_admin(
    current_user: UserPublic = Depends(get_current_user()),
) -> UserPublic:
    """Require admin role for endpoint access.

    Args:
        current_user: Current authenticated user from dependency

    Returns:
        UserPublic if user is admin

    Raises:
        HTTPException: If user is not admin
    """
    logger.info(
        f"👮 [Admin Check] Checking admin access for user: {current_user.email} (role: {current_user.role})"
    )
    # Check if user has admin role
    if current_user.role != UserRole.ADMIN.value:
        logger.warning(
            f"👮 [Admin Check] Access denied - user {current_user.email} has role '{current_user.role}', required: '{UserRole.ADMIN.value}'"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    logger.info(f"👮 [Admin Check] Admin access granted for user: {current_user.email}")
    return current_user
