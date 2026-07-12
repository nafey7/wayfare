"""Google Places API endpoints.

Provides place search (Text Search API) and photo retrieval (Place Photos API).
Photos are proxied through the backend so the API key is never exposed to the client.
Request/response logging via LoggingMiddleware (places_logger) and client-level logs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.logging import get_places_logger
from app.core.places_rate_limit import (
    check_places_photo_rate_limit,
    check_places_search_rate_limit,
)
from app.domains.auth.dependencies import require_authenticated
from app.domains.user.schemas import UserPublic
from integrations.googleplaces.client import (
    PHOTO_RESOURCE_PATTERN,
    GooglePlacesClient,
    PlacesAPIError,
    get_places_client,
)

logger = get_places_logger()
router = APIRouter(prefix="/places", tags=["Places"])

_places_client: GooglePlacesClient | None = None


def _get_client() -> GooglePlacesClient:
    """Lazy-initialize Places client."""
    global _places_client
    if _places_client is None:
        _places_client = get_places_client()
    return _places_client


async def close_places_client() -> None:
    """Close the shared Places client's httpx connection. Call on app shutdown."""
    global _places_client
    if _places_client is not None:
        await _places_client.aclose()
        _places_client = None


def _places_error_to_http(e: PlacesAPIError) -> HTTPException:
    """Convert PlacesAPIError to HTTPException for consistent error responses."""
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


# =============================================================================
# Schemas
# =============================================================================


class PlaceSearchRequest(BaseModel):
    """Request body for place text search."""

    text_query: str = Field(
        ...,
        alias="textQuery",
        description="Place or location name (e.g., 'Eiffel Tower')",
        min_length=1,
        max_length=500,
    )
    language_code: str = Field("en", alias="languageCode")
    page_size: int = Field(5, ge=1, le=20, alias="pageSize")
    page_token: str | None = Field(None, alias="pageToken")

    model_config = {"populate_by_name": True}


class PlacePhotoRef(BaseModel):
    """Photo reference from a place (for client to request image via /photos/.../media)."""

    name: str = Field(
        ...,
        description="Resource name for getMedia, e.g. places/ChIJ.../photos/ATCD...",
    )
    width_px: int | None = Field(None, alias="widthPx", description="Original width")
    height_px: int | None = Field(None, alias="heightPx", description="Original height")

    model_config = {"populate_by_name": True}


class PlaceSearchResult(BaseModel):
    """Single place from text search."""

    id: str = Field(..., description="Place ID")
    display_name: str = Field(..., alias="displayName", description="Place name")
    formatted_address: str | None = Field(
        None, alias="formattedAddress", description="Full address"
    )
    photos: list[PlacePhotoRef] = Field(default_factory=list, description="Photo refs")
    rating: float | None = Field(None, description="User rating 0-5")
    location: dict[str, float] | None = Field(None, description="lat/lng if requested")

    model_config = {"populate_by_name": True}


class PlaceSearchResponse(BaseModel):
    """Response from place text search."""

    places: list[PlaceSearchResult] = Field(..., description="Matching places")
    next_page_token: str | None = Field(
        None, alias="nextPageToken", description="For pagination"
    )

    model_config = {"populate_by_name": True}


class PlaceImageUrlResponse(BaseModel):
    """Response with protected proxy URL for the top place's first photo."""

    image_url: str = Field(
        ...,
        alias="imageUrl",
        description=(
            "Authenticated proxy URL for fetching the image through the backend."
        ),
    )

    model_config = {"populate_by_name": True}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/image-url", response_model=PlaceImageUrlResponse)
async def get_place_image_url(
    request: Request,
    _user: UserPublic = Depends(require_authenticated),
    place: str = Query(
        ...,
        description="Place name (e.g., 'Eiffel Tower', 'Statue of Liberty')",
        min_length=1,
    ),
    max_width_px: int = Query(800, ge=1, le=4800, description="Max image width in URL"),
) -> PlaceImageUrlResponse:
    """
    Get proxy image URL for the most relevant place matching the name.

    Performs text search, takes the first place's first photo, and returns
    a URL pointing to our backend that proxies the image. Clients should fetch
    the URL with Authorization headers rather than binding it directly to
    <img src="...">.
    """
    if not check_places_search_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    try:
        try:
            client = _get_client()
            image_url = await client.resolve_place_image_url(place, max_width_px)
        except PlacesAPIError as e:
            raise _places_error_to_http(e) from e

        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No image found for: {place}",
            )

        logger.info(
            f"PLACES API | image-url | place={place!r} | imageUrl=<proxy>",
            extra={"endpoint": "image-url", "place": place},
        )
        return PlaceImageUrlResponse(imageUrl=image_url)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Places API | image-url | error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Places API error",
        ) from e


@router.post("/search", response_model=PlaceSearchResponse)
async def search_places(
    request: Request,
    body: PlaceSearchRequest,
    _user: UserPublic = Depends(require_authenticated),
) -> PlaceSearchResponse:
    """
    Search for places by text query using Google Places Text Search API.

    Returns places with id, displayName, formattedAddress, photos.
    Use the photo `name` with GET /api/places/photos/{name}/media to retrieve images.
    """
    if not check_places_search_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    try:
        try:
            client = _get_client()
            raw_places, next_token = await client.search_text(
                body.text_query,
                language_code=body.language_code,
                page_size=body.page_size,
                page_token=body.page_token,
            )
        except PlacesAPIError as e:
            raise _places_error_to_http(e) from e

        # Transform to response schema
        places_out: list[PlaceSearchResult] = []
        for p in raw_places:
            display_name = "Unknown"
            if "displayName" in p and isinstance(p["displayName"], dict):
                display_name = p["displayName"].get("text", "Unknown")
            elif isinstance(p.get("displayName"), str):
                display_name = p["displayName"]

            photos_raw = p.get("photos") or []
            photos: list[PlacePhotoRef] = []
            for ph in photos_raw:
                if isinstance(ph, dict) and ph.get("name"):
                    photos.append(
                        PlacePhotoRef(
                            name=ph["name"],
                            widthPx=ph.get("widthPx"),
                            heightPx=ph.get("heightPx"),
                        )
                    )

            places_out.append(
                PlaceSearchResult(
                    id=p.get("id", ""),
                    displayName=display_name,
                    formattedAddress=p.get("formattedAddress"),
                    photos=photos,
                    rating=p.get("rating"),
                    location=p.get("location"),
                )
            )

        logger.info(
            f"PLACES API | search | textQuery={body.text_query!r} | places={len(places_out)}",
            extra={
                "endpoint": "search",
                "text_query": body.text_query,
                "places_count": len(places_out),
            },
        )
        return PlaceSearchResponse(places=places_out, nextPageToken=next_token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Places API | search | error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Places API error",
        ) from e


@router.get("/photos/{photo_path:path}/media")
async def get_place_photo(
    request: Request,
    photo_path: str,
    _user: UserPublic = Depends(require_authenticated),
    max_width_px: int = Query(800, ge=1, le=4800, description="Max image width"),
    max_height_px: int | None = Query(None, ge=1, le=4800, description="Max height"),
) -> Response:
    """
    Stream place photo by resource name. Backend fetches from Google to keep API key hidden.

    The photo_path should be the full resource name from search results, e.g.:
    places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/ATCD...

    URL example: /api/places/photos/places/ChIJ.../photos/ATCD.../media?maxWidthPx=400
    """
    if not check_places_photo_rate_limit(request):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    # Reconstruct full resource name (path may omit leading "places/")
    resource_name = photo_path.strip().lstrip("/")
    if not resource_name.startswith("places/"):
        resource_name = f"places/{resource_name}"
    if not PHOTO_RESOURCE_PATTERN.match(resource_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo resource name",
        )

    try:
        try:
            client = _get_client()
            image_bytes, content_type = await client.get_photo_media(
                resource_name,
                max_width_px=max_width_px,
                max_height_px=max_height_px,
            )
        except PlacesAPIError as e:
            raise _places_error_to_http(e) from e

        return Response(
            content=image_bytes,
            media_type=content_type,
            # private: auth-gated; shared caches must not store (browser may still cache)
            headers={"Cache-Control": "private, max-age=86400"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Places API | photo media | error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Places API error",
        ) from e
