"""Short-lived JWT for guest access to public Places photo proxy."""

from __future__ import annotations

import ipaddress
import time
from typing import Literal

import jwt

from app.core.config import settings

PLACES_SESSION_JWT_TYPE = "places_session"


class PlacesSessionTokenError(Exception):
    """Validation failure for a places session token."""

    def __init__(
        self,
        reason: Literal[
            "expired",
            "ip_mismatch",
            "invalid",
            "wrong_type",
            "session_mismatch",
        ],
        message: str | None = None,
    ) -> None:
        self.reason = reason
        super().__init__(message or reason)


def _places_signing_key() -> str:
    secret = (settings.PLACES_SESSION_TOKEN_SECRET or "").strip()
    if secret:
        return secret
    return f"{settings.SECRET_KEY}_places"


def client_ip_to_prefix(client_ip: str) -> str:
    """IPv4: first three octets. IPv6: first 48 bits (three hextets)."""
    raw = (client_ip or "").strip()
    if not raw:
        return "unknown"
    try:
        addr = ipaddress.ip_address(raw)
    except ValueError:
        return "unknown"
    if isinstance(addr, ipaddress.IPv4Address):
        parts = str(addr).split(".")
        return ".".join(parts[:3]) if len(parts) >= 3 else str(addr)
    exploded = addr.exploded.split(":")
    return ":".join(exploded[:3])


def mint_places_session_token(session_id: str, client_ip: str) -> str:
    """Sign a short-lived JWT bound to guest session and client IP prefix."""
    now = int(time.time())
    expire_seconds = max(60, int(settings.PLACES_SESSION_TOKEN_EXPIRE_MINUTES) * 60)
    payload = {
        "type": PLACES_SESSION_JWT_TYPE,
        "session_id": session_id,
        "ip_prefix": client_ip_to_prefix(client_ip),
        "iat": now,
        "exp": now + expire_seconds,
    }
    return jwt.encode(payload, _places_signing_key(), algorithm="HS256")


def validate_places_session_token(token: str, session_id: str, client_ip: str) -> None:
    """Verify JWT signature, type, expiry, session id, and IP prefix.

    Raises:
        PlacesSessionTokenError: On any validation failure.
    """
    if not token or not token.strip():
        raise PlacesSessionTokenError("invalid", "Missing token")
    try:
        payload = jwt.decode(
            token.strip(),
            _places_signing_key(),
            algorithms=["HS256"],
            options={"require": ["exp", "iat"]},
        )
    except jwt.ExpiredSignatureError:
        raise PlacesSessionTokenError("expired") from None
    except jwt.InvalidTokenError:
        raise PlacesSessionTokenError("invalid") from None

    if payload.get("type") != PLACES_SESSION_JWT_TYPE:
        raise PlacesSessionTokenError("wrong_type")

    if payload.get("session_id") != session_id:
        raise PlacesSessionTokenError("session_mismatch")

    expected_prefix = client_ip_to_prefix(client_ip)
    if payload.get("ip_prefix") != expected_prefix:
        raise PlacesSessionTokenError("ip_mismatch")
