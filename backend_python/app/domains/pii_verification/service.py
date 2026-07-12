"""PII verification service - orchestrate OTP request, email send, verify, token creation."""

import logging
from datetime import timedelta

import jwt

from app.core.config import settings
from app.domains.common import now_utc
from app.domains.email.enums import EmailType
from app.domains.email.service import EmailService
from app.domains.user.schemas import UserPublic

from .repository import (
    PII_VIEW_TOKEN_EXPIRE_MINUTES,
    check_pii_request_rate_limit,
    create_challenge,
    mask_email,
    record_pii_request,
    verify_otp,
)
from .schemas import (
    PiiVerificationRequestResponse,
    PiiVerificationVerifyResponse,
)

logger = logging.getLogger(__name__)

PII_VIEW_TOKEN_AUDIENCE = "pii-view"  # noqa: S105 # nosec B105 - JWT audience string, not password


def create_pii_view_token(user_id: str) -> str:
    """Create short-lived JWT for PII view access (~2 min)."""
    payload = {
        "user_id": str(user_id),
        "aud": PII_VIEW_TOKEN_AUDIENCE,
        "exp": now_utc() + timedelta(minutes=PII_VIEW_TOKEN_EXPIRE_MINUTES),
        "iat": now_utc(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_pii_view_token(token: str) -> str | None:
    """Verify PII view token and return user_id or None."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience=PII_VIEW_TOKEN_AUDIENCE,
        )
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def request_pii_verification(user: UserPublic) -> PiiVerificationRequestResponse:
    """Request PII verification: create challenge, send OTP email, return challenge_id + masked email."""
    email = user.email or ""
    if not email:
        raise ValueError("User has no email address for verification")

    allowed, rate_limit_error = await check_pii_request_rate_limit(str(user.id))
    if not allowed:
        raise ValueError(rate_limit_error or "Too many requests.")

    await record_pii_request(str(user.id))
    challenge_id, otp = await create_challenge(str(user.id), email)

    await EmailService.send_email(
        EmailType.PII_VERIFICATION_OTP,
        email,
        context={"otp": otp, "masked_email": mask_email(email)},
    )

    return PiiVerificationRequestResponse(
        challenge_id=challenge_id,
        masked_email=mask_email(email),
    )


async def verify_pii_otp(
    user: UserPublic, challenge_id: str, code: str
) -> PiiVerificationVerifyResponse:
    """Verify OTP and return PII view token on success."""
    success, error_msg = await verify_otp(challenge_id, str(user.id), code)
    if not success:
        raise ValueError(error_msg or "Verification failed")

    token = create_pii_view_token(str(user.id))
    return PiiVerificationVerifyResponse(
        pii_view_token=token,
        expires_in_seconds=PII_VIEW_TOKEN_EXPIRE_MINUTES * 60,
    )
