"""Parse X-Public-Chat-Session for guest public APIs (chat, places)."""

import uuid

from fastapi import HTTPException, status


def parse_guest_session_id_header(raw: str | None) -> str:
    """Return a canonical UUID string from the header value, or raise HTTP 400."""
    if not raw or not str(raw).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing or empty X-Public-Chat-Session header",
        )
    try:
        parsed = uuid.UUID(str(raw).strip())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Public-Chat-Session: must be a UUID",
        ) from e
    return str(parsed)
