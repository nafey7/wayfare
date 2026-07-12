"""Guest Places photo proxy — session JWT + always-on rate limits."""

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import Response

from app.core.feature_flags import public_chat_enabled
from app.core.logging import get_places_logger
from app.core.places_session import (
    PlacesSessionTokenError,
    mint_places_session_token,
    validate_places_session_token,
)
from app.core.public_guest_session_header import parse_guest_session_id_header
from app.core.public_places_rate_limit import (
    check_public_places_rate_limit,
    check_public_places_session_token_refresh_rate_limit,
    get_trusted_request_client_ip,
    record_public_places_session_photo_success,
)
from integrations.googleplaces.client import (
    PHOTO_RESOURCE_PATTERN,
    GooglePlacesClient,
    PlacesAPIError,
    get_places_client,
)

logger = get_places_logger()
router = APIRouter(prefix="/public/places", tags=["Public Places"])

_public_places_client: GooglePlacesClient | None = None


def _get_public_places_client() -> GooglePlacesClient:
    global _public_places_client
    if _public_places_client is None:
        _public_places_client = get_places_client()
    return _public_places_client


@router.post("/session-token")
async def mint_guest_places_session_token(
    request: Request,
    x_public_chat_session: Annotated[
        str | None, Header(alias="X-Public-Chat-Session")
    ] = None,
) -> dict[str, str]:
    """Mint a new Places session JWT for the guest (e.g. after the previous token expired).

    Does not consume per-session photo quota. Rate-limited per IP separately from photo GETs.
    """
    if not public_chat_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public chat is disabled.",
        )
    session_id = parse_guest_session_id_header(x_public_chat_session)
    if not check_public_places_session_token_refresh_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Places session refresh rate limit exceeded.",
            headers={"Retry-After": "60"},
        )
    client_ip = get_trusted_request_client_ip(request)
    token = mint_places_session_token(session_id, client_ip)
    return {"places_session_token": token}


async def close_public_places_client() -> None:
    """Close the guest Places proxy client on app shutdown."""
    global _public_places_client
    if _public_places_client is not None:
        await _public_places_client.aclose()
        _public_places_client = None


def _places_error_to_http(e: PlacesAPIError) -> HTTPException:
    """Convert PlacesAPIError to HTTPException (mirrors app.api.places)."""
    if e.status_code == 404 or "not found" in (e.message or "").lower():
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message or "Not found",
        )
    if e.status_code and 400 <= e.status_code < 500:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message or "Bad request",
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Places API error",
    )


@router.get("/photos/{photo_path:path}/media")
async def get_public_place_photo(
    request: Request,
    photo_path: str,
    x_places_session_token: Annotated[
        str | None, Header(alias="X-Places-Session-Token")
    ] = None,
    x_public_chat_session: Annotated[
        str | None, Header(alias="X-Public-Chat-Session")
    ] = None,
    max_width_px: int = Query(800, ge=1, le=4800, description="Max image width"),
    max_height_px: int | None = Query(None, ge=1, le=4800, description="Max height"),
) -> Response:
    """Stream a place photo for guests with a valid short-lived session token."""
    session_id = parse_guest_session_id_header(x_public_chat_session)
    _sp = session_id[:8]
    if not x_places_session_token or not str(x_places_session_token).strip():
        logger.info(
            "public_places_proxy | outcome=http_401 | reason=missing_token | session_prefix=%s",
            _sp,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Places-Session-Token header",
        )

    client_ip = get_trusted_request_client_ip(request)
    try:
        validate_places_session_token(
            str(x_places_session_token).strip(), session_id, client_ip
        )
    except PlacesSessionTokenError as e:
        if e.reason in ("expired", "ip_mismatch", "session_mismatch"):
            logger.info(
                "public_places_proxy | outcome=http_403 | reason=%s | session_prefix=%s",
                e.reason,
                _sp,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Places session token invalid or expired",
            ) from e
        logger.info(
            "public_places_proxy | outcome=http_401 | reason=invalid_token | session_prefix=%s",
            _sp,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid places session token",
        ) from e

    if not check_public_places_rate_limit(request, session_id):
        logger.warning(
            "public_places_proxy | outcome=http_429 | reason=rate_limit | session_prefix=%s",
            _sp,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
            headers={"Retry-After": "60"},
        )

    resource_name = photo_path.strip().lstrip("/")
    if not resource_name.startswith("places/"):
        resource_name = f"places/{resource_name}"
    if not PHOTO_RESOURCE_PATTERN.match(resource_name):
        logger.info(
            "public_places_proxy | outcome=http_400 | reason=bad_resource | session_prefix=%s",
            _sp,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo resource name",
        )

    try:
        try:
            client = _get_public_places_client()
            image_bytes, content_type = await client.get_photo_media(
                resource_name,
                max_width_px=max_width_px,
                max_height_px=max_height_px,
            )
        except PlacesAPIError as e:
            upstream = _places_error_to_http(e)
            logger.info(
                "public_places_proxy | outcome=http_%s | reason=places_api | session_prefix=%s",
                upstream.status_code,
                _sp,
            )
            raise upstream from e

        record_public_places_session_photo_success(session_id)
        logger.debug(
            "public_places_proxy | outcome=http_200 | session_prefix=%s | bytes=%d",
            _sp,
            len(image_bytes),
        )
        return Response(
            content=image_bytes,
            media_type=content_type,
            # private: session-gated; shared caches must not store (would bypass token checks
            # and rate limits). Browser may still cache for the TTL.
            headers={"Cache-Control": "private, max-age=2592000"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Public Places API | photo media | error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Places API error",
        ) from e
