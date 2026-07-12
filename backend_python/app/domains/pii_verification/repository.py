"""PII verification repository - store and validate OTP challenges (HMAC only)."""

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import settings
from app.database.constants import (
    PII_VERIFICATION_CHALLENGES_COLLECTION,
    PII_VERIFICATION_RATE_LIMIT_COLLECTION,
)
from app.database.dependencies import get_database

logger = logging.getLogger(__name__)

OTP_EXPIRE_MINUTES = 10
MAX_ATTEMPTS = 5
PII_VIEW_TOKEN_EXPIRE_MINUTES = 2
PII_REQUEST_RATE_LIMIT_COUNT = 3
PII_REQUEST_RATE_LIMIT_MINUTES = 5


def _hmac_digest(challenge_id: str, code: str) -> str:
    """Compute HMAC of (challenge_id:code) with server secret. Never log code."""
    secret = settings.SECRET_KEY.encode()
    message = f"{challenge_id}:{code}".encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _generate_otp() -> str:
    """Generate 6-digit OTP using OS CSPRNG."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def create_challenge(user_id: str, user_email: str) -> tuple[str, str]:
    """Create OTP challenge: generate code, store HMAC, return (challenge_id, raw_otp).

    Invalidate any existing challenge for this user first.
    Returns:
        (challenge_id, raw_otp) - raw_otp is only for sending via email; never logged or stored.
    """
    db = await get_database()
    coll = db[PII_VERIFICATION_CHALLENGES_COLLECTION]

    await coll.delete_many({"user_id": ObjectId(user_id)})

    otp = _generate_otp()
    challenge_id = str(ObjectId())
    # Use timezone-aware UTC to match PyMongo (returns aware datetimes from BSON)
    expires_at = datetime.now(UTC) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    doc = {
        "challenge_id": challenge_id,
        "user_id": ObjectId(user_id),
        "user_email": user_email,
        "otp_hmac": _hmac_digest(challenge_id, otp),
        "attempts": 0,
        "expires_at": expires_at,
    }
    await coll.insert_one(doc)
    return challenge_id, otp


def mask_email(email: str) -> str:
    """Mask email for display: j***@gmail.com."""
    if not email or "@" not in email:
        return "***@***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def _normalize_to_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware UTC for safe comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


async def check_pii_request_rate_limit(user_id: str) -> tuple[bool, str | None]:
    """Check if user is within OTP request rate limit (max 3 per 5 minutes).

    Returns:
        (allowed, error_message) - error_message is None if allowed.
    """
    db = await get_database()
    coll = db[PII_VERIFICATION_RATE_LIMIT_COLLECTION]
    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return False, "Invalid user."

    cutoff = datetime.now(UTC) - timedelta(minutes=PII_REQUEST_RATE_LIMIT_MINUTES)
    count = await coll.count_documents(
        {"user_id": user_oid, "requested_at": {"$gt": cutoff}}
    )
    if count >= PII_REQUEST_RATE_LIMIT_COUNT:
        return (
            False,
            f"Too many verification requests. Try again in {PII_REQUEST_RATE_LIMIT_MINUTES} minutes.",
        )
    return True, None


async def record_pii_request(user_id: str) -> None:
    """Record an OTP request for rate limiting. Call after rate limit check passes."""
    db = await get_database()
    coll = db[PII_VERIFICATION_RATE_LIMIT_COLLECTION]
    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return
    await coll.insert_one(
        {
            "user_id": user_oid,
            "requested_at": datetime.now(UTC),
        }
    )


async def verify_otp(
    challenge_id: str, user_id: str, code: str
) -> tuple[bool, str | None]:
    """Verify OTP code. Returns (success, error_message).

    On success: invalidate challenge.
    On failure: increment attempts; if >= MAX_ATTEMPTS, invalidate.
    """
    db = await get_database()
    coll = db[PII_VERIFICATION_CHALLENGES_COLLECTION]

    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return (
            False,
            "Invalid or expired verification request. Please request a new code.",
        )

    # Fetch by challenge/user only - avoid datetime in query (MongoDB/PyMongo naive/aware issues)
    doc = await coll.find_one({"challenge_id": challenge_id, "user_id": user_oid})
    if not doc:
        return (
            False,
            "Invalid or expired verification request. Please request a new code.",
        )

    expires_at = doc.get("expires_at")
    if expires_at is None:
        return (
            False,
            "Invalid or expired verification request. Please request a new code.",
        )
    now_utc = _normalize_to_utc(datetime.now(UTC))
    exp_utc = _normalize_to_utc(expires_at)
    if now_utc >= exp_utc:
        await coll.delete_one({"_id": doc["_id"]})
        return (
            False,
            "Invalid or expired verification request. Please request a new code.",
        )

    attempts = doc.get("attempts", 0)
    if attempts >= MAX_ATTEMPTS:
        await coll.delete_one({"_id": doc["_id"]})
        return False, "Too many incorrect attempts. Please request a new code."

    expected_hmac = doc["otp_hmac"]
    computed_hmac = _hmac_digest(challenge_id, code)

    if not hmac.compare_digest(expected_hmac, computed_hmac):
        await coll.update_one(
            {"_id": doc["_id"]},
            {"$inc": {"attempts": 1}},
        )
        remaining = MAX_ATTEMPTS - attempts - 1
        if remaining <= 0:
            return False, "Too many incorrect attempts. Please request a new code."
        return False, f"Incorrect code. {remaining} attempt(s) remaining."

    await coll.delete_one({"_id": doc["_id"]})
    return True, None


async def get_challenge(challenge_id: str, user_id: str) -> dict[str, Any] | None:
    """Get challenge doc if valid. Used to check expiry before verify."""
    db = await get_database()
    coll = db[PII_VERIFICATION_CHALLENGES_COLLECTION]

    try:
        user_oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None

    doc = await coll.find_one(
        {
            "challenge_id": challenge_id,
            "user_id": user_oid,
        }
    )
    return dict(doc) if doc else None
