"""Shared logic for exchanging booking tokens for session tokens.

Used by both flight and hotel booking-auth endpoints when the user opens
a booker (e.g. from chat) with a short-lived auth_token in the URL.
"""

import logging

import jwt

from app.core.config import settings
from app.domains.auth.service import AuthService
from app.domains.user.service import UserService

logger = logging.getLogger(__name__)


async def exchange_booking_token(
    auth_token: str | None,
    current_user_id: str | None = None,
) -> dict:
    """Exchange a short-lived booking token for session tokens.

    Validates the JWT (type=booking_auth), loads the user, creates a session,
    and returns access_token, refresh_token, and related fields.

    When current_user_id is provided (caller is already logged in), the token's
    user_id must match; otherwise returns 403 so a user cannot use another
    account's email link.

    Returns:
        dict with keys: access_token, refresh_token, token_type, user_id, session_id

    Raises:
        HTTPException: 400 if auth_token missing or invalid type,
            401 if token expired or invalid, 403 if current user != token user,
            404 if user not found.
    """
    from fastapi import HTTPException, status

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth_token required",
        )

    try:
        payload = jwt.decode(auth_token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Booking token expired",
        ) from None
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid booking token",
        ) from None

    user_id = payload.get("user_id")
    token_type = payload.get("type")
    if token_type != "booking_auth":  # nosec B105 - token type identifier
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )

    # If caller is already logged in, the link must belong to the same account
    if current_user_id is not None and str(user_id) != str(current_user_id):
        logger.warning(
            "Booking auth token user mismatch: token user_id=%s, current user_id=%s",
            user_id,
            current_user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This link is for a different account. Sign out and open the link again, or use your own bookings.",
        )

    user = await UserService.get_user_public(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    session, access_token, refresh_token = await AuthService.create_session(
        str(user.id),
        fingerprint=None,
        ip_address=None,
        user_agent=None,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "session_id": str(session.id) if session.id else None,
    }
