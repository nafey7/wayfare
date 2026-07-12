"""Google Places API (New) client.

Implements:
1. Text Search API (places:searchText) - resolve location names to places with photos
2. Place Photos API (places.photos.getMedia) - fetch image by photo resource name

Uses X-Goog-FieldMask for cost control - only request fields actually needed.
"""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.logging import get_places_logger

logger = get_places_logger()

# SSRF protection: strict pattern for Google Places photo resource names
PHOTO_RESOURCE_PATTERN = re.compile(r"^places/[A-Za-z0-9_-]+/photos/[A-Za-z0-9_-]+$")


def _redact_credentials(data: dict) -> dict:
    """Remove sensitive fields before logging.

    Note: Only top-level dict keys are redacted. Sufficient for Google error
    responses; nested structures (e.g. error.details[].field) are not recursed.
    """
    redacted = data.copy()
    for key in ("api_key", "X-Goog-Api-Key", "user_id", "user_password", "password"):
        if key in redacted:
            redacted[key] = "***REDACTED***"
    return redacted


TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_BASE_URL = "https://places.googleapis.com/v1"

# Field mask for text search: id, displayName, formattedAddress, photos (minimal for cost)
TEXT_SEARCH_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.photos,"
    "places.location,places.rating,nextPageToken"
)
API_TIMEOUT = 15.0
# Max photo size to prevent memory exhaustion (5MB)
MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024


class PlacesAPIError(Exception):
    """Raised when Places API call fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GooglePlacesClient:
    """Client for Google Places API (New) - Text Search and Place Photos."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Places API client.

        Args:
            api_key: Google API key. If not provided, loads from settings.

        When ``settings.PLACES_API_ENABLED`` is False, ``self.api_key`` is
        forced to ``None`` regardless of what's configured — the existing
        ``if not self.api_key`` guards in :meth:`search_text` and
        :meth:`get_photo_media` then short-circuit every code path that
        reaches the API.
        """
        if not settings.PLACES_API_ENABLED:
            self.api_key: str | None = None
            logger.warning(
                "Google Places API disabled via PLACES_API_ENABLED=false "
                "- all Places calls will be skipped"
            )
        else:
            self.api_key = (
                api_key or settings.GOOGLE_API_KEY or settings.GOOGLE_MAPS_API_KEY
            )
            if not self.api_key:
                logger.warning(
                    "GOOGLE_API_KEY not configured - Places API will be unavailable"
                )
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create shared httpx client for connection pooling."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=API_TIMEOUT,
                follow_redirects=True,
            )
        return self._http_client

    async def aclose(self) -> None:
        """Close the httpx client. Call on application shutdown for proper cleanup."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def search_text(
        self,
        text_query: str,
        *,
        language_code: str = "en",
        page_size: int = 5,
        page_token: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Search for places by text query (e.g., "Eiffel Tower", "Statue of Liberty").

        Args:
            text_query: Location or place name to search
            language_code: Preferred language for results (default: en)
            page_size: Max results per page (1-20, default 5)
            page_token: Token from previous response for pagination

        Returns:
            Tuple of (places list, next_page_token).
            Each photo in places[].photos[] has a "name" (resource name) for getMedia.

        Raises:
            PlacesAPIError: If API call fails
        """
        if not self.api_key:
            raise PlacesAPIError(
                "Google API key not configured. Set GOOGLE_API_KEY or GOOGLE_MAPS_API_KEY."
            )

        payload: dict[str, Any] = {
            "textQuery": text_query,
            "languageCode": language_code,
            "pageSize": min(max(page_size, 1), 20),
        }
        if page_token:
            payload["pageToken"] = page_token

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": TEXT_SEARCH_FIELD_MASK,
        }

        logger.info(
            f"PLACES REQUEST | searchText | textQuery={text_query!r}",
            extra={
                "operation": "searchText",
                "text_query": text_query,
                "language_code": language_code,
                "page_size": payload["pageSize"],
            },
        )

        try:
            start_time = time.time()
            client = await self._get_client()
            response = await client.post(
                TEXT_SEARCH_URL,
                json=payload,
                headers=headers,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"PLACES RESPONSE | searchText | status={response.status_code} | "
                    f"textQuery={text_query!r} | {duration_ms}ms",
                    extra={
                        "operation": "searchText",
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
                self._raise_places_error(response)

            data = response.json()
            places = data.get("places", [])
            next_token = data.get("nextPageToken") or None
            logger.info(
                f"PLACES RESPONSE | searchText | textQuery={text_query!r} | "
                f"places={len(places)} | {duration_ms}ms",
                extra={
                    "operation": "searchText",
                    "text_query": text_query,
                    "places_count": len(places),
                    "duration_ms": duration_ms,
                },
            )
            return places, next_token

        except httpx.RequestError as e:
            logger.error(f"Places API request failed: {e}")
            raise PlacesAPIError(f"Places API request failed: {e!s}") from e

    async def get_photo_media(
        self,
        photo_resource_name: str,
        *,
        max_width_px: int = 800,
        max_height_px: int | None = None,
    ) -> tuple[bytes, str]:
        """Fetch photo image bytes by resource name.

        The photo_resource_name is from places[].photos[].name, e.g.:
        places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD...

        Backend fetches and returns bytes so the API key is never exposed to the client.

        Args:
            photo_resource_name: Full resource name (places/.../photos/...)
            max_width_px: Max image width in pixels (1-4800)
            max_height_px: Max image height (optional; one of max_width/max_height required)

        Returns:
            Tuple of (raw image bytes, content_type from upstream, e.g. image/jpeg or image/png)

        Raises:
            PlacesAPIError: If API call fails or image exceeds MAX_PHOTO_SIZE_BYTES
        """
        if not self.api_key:
            raise PlacesAPIError(
                "Google API key not configured. Set GOOGLE_API_KEY or GOOGLE_MAPS_API_KEY."
            )

        if not max_width_px and not max_height_px:
            raise PlacesAPIError(
                "At least one of maxWidthPx or maxHeightPx must be specified"
            )

        # Normalize: ensure no leading slash, convert to media path
        name = photo_resource_name.strip().lstrip("/")
        if not name.startswith("places/"):
            name = f"places/{name}"
        if not PHOTO_RESOURCE_PATTERN.match(name):
            raise PlacesAPIError(f"Invalid photo resource name: {name}")

        media_url = f"{PLACES_BASE_URL}/{name}/media"
        params: dict[str, int] = {}
        if max_width_px:
            params["maxWidthPx"] = min(max(max_width_px, 1), 4800)
        if max_height_px:
            params["maxHeightPx"] = min(max(max_height_px, 1), 4800)

        headers = {"X-Goog-Api-Key": self.api_key}

        # Truncate long photo ref for logs
        ref_preview = name[:80] + "..." if len(name) > 80 else name
        logger.info(
            f"PLACES REQUEST | getMedia | resource={ref_preview}",
            extra={
                "operation": "getMedia",
                "resource_preview": ref_preview,
                "max_width_px": params.get("maxWidthPx"),
                "max_height_px": params.get("maxHeightPx"),
            },
        )

        try:
            start_time = time.time()
            client = await self._get_client()
            response = await client.get(
                media_url,
                params=params,
                headers=headers,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            if response.status_code != 200:
                logger.error(
                    f"PLACES RESPONSE | getMedia | status={response.status_code} | "
                    f"resource={ref_preview} | {duration_ms}ms",
                    extra={
                        "operation": "getMedia",
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
                self._raise_places_error(response)

            content_type = response.headers.get("content-type", "image/jpeg")
            if ";" in content_type:
                content_type = content_type.split(";")[0].strip()
            content_type = content_type or "image/jpeg"

            # Note: client.get() buffers the full response before we iterate.
            # MAX_PHOTO_SIZE_BYTES is enforced post-buffering. For true streaming
            # protection (reject oversized responses before full read), use
            # client.stream("GET", ...) and check Content-Length or stream with early abort.
            chunks: list[bytes] = []
            total_size = 0
            async for chunk in response.aiter_bytes():
                total_size += len(chunk)
                if total_size > MAX_PHOTO_SIZE_BYTES:
                    raise PlacesAPIError(
                        f"Photo exceeds maximum size ({MAX_PHOTO_SIZE_BYTES} bytes)"
                    )
                chunks.append(chunk)
            content = b"".join(chunks)

            logger.info(
                f"PLACES RESPONSE | getMedia | resource={ref_preview} | "
                f"size_bytes={len(content)} | {duration_ms}ms",
                extra={
                    "operation": "getMedia",
                    "size_bytes": len(content),
                    "duration_ms": duration_ms,
                },
            )
            return content, content_type

        except httpx.RequestError as e:
            logger.error(f"Places photo media request failed: {e}")
            raise PlacesAPIError(f"Places photo request failed: {e!s}") from e

    async def resolve_place_image_url(
        self,
        place: str,
        max_width_px: int = 400,
    ) -> str | None:
        """Resolve a place name to a proxy image URL.

        Searches for the place via Text Search API, extracts the first photo's
        resource name, and returns a proxy URL through our backend.

        Args:
            place: Place name to search for (e.g., "Senso-ji Temple Tokyo")
            max_width_px: Maximum image width in pixels

        Returns:
            Proxy image URL string, or None if no image found or on error.
        """
        try:
            raw_places, _ = await self.search_text(
                place, language_code="en", page_size=1
            )
            if not raw_places:
                return None

            photos = raw_places[0].get("photos") or []
            if not photos or not isinstance(photos[0], dict):
                return None

            photo_name = photos[0].get("name")
            if not photo_name:
                return None

            base = settings.BACKEND_URL.rstrip("/")
            encoded_path = quote(photo_name.strip().lstrip("/"), safe="/")
            return (
                f"{base}/api/places/photos/{encoded_path}/media"
                f"?maxWidthPx={max_width_px}"
            )
        except PlacesAPIError as e:
            logger.warning(
                f"PLACES API | resolve_place_image_url | place={place!r} | "
                f"error={e.message}",
            )
            return None

    def _raise_places_error(self, response: httpx.Response) -> None:
        """Extract error from response and raise PlacesAPIError."""
        try:
            err_data = response.json()
            err_obj = err_data.get("error", {})
            msg = err_obj.get("message", response.text or str(response.status_code))
            logger.error(
                "Places API error response: %s",
                _redact_credentials(err_data)
                if isinstance(err_data, dict)
                else err_data,
            )
        except Exception:
            msg = response.text or f"HTTP {response.status_code}"
        raise PlacesAPIError(msg, response.status_code)


def get_places_client() -> GooglePlacesClient:
    """Get a Google Places API client instance."""
    return GooglePlacesClient()
