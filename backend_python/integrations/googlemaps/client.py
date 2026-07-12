"""Google Maps Platform Routes API client.

Handles communication with Google Maps Routes API for transit route planning.
Follows the same pattern as FlightLogic integration with DTOs and adapters.
"""

import json
import logging
from typing import TypedDict

import httpx

from app.core.config import settings
from app.domains.transit.exceptions import TransitRouteError
from app.domains.transit.schemas import TransitRouteRequest, TransitRouteResponse

from .adapter import GoogleMapsSchemaAdapter
from .dto import TransitRouteResponseDTO

logger = logging.getLogger(__name__)

# Google Maps Routes API endpoint
ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Field masks for different use cases.
#
# _TRANSIT_FIELD_MASK is intentionally scoped to polyline + leg coordinates for
# map display only.  Step-level fields (stop names, agency info, travel modes,
# transit details) are excluded because the current transit API consumer only
# needs the route geometry.  The adapter contains step-parsing logic so that
# callers who need full step data can pass _TRANSIT_FULL_FIELD_MASK (or a
# custom mask) to compute_routes(); it is covered by unit tests using synthetic
# DTO payloads.
_TRANSIT_FIELD_MASK = (
    "routes.duration,routes.distanceMeters,"
    "routes.polyline.encodedPolyline,routes.localizedValues,"
    "routes.legs.startLocation.latLng,routes.legs.endLocation.latLng"
)

# Extended mask that also includes step-level transit details (stop names,
# agency info, travel mode, navigation instructions).  Use this when a consumer
# needs to render turn-by-turn or transit step cards.
_TRANSIT_FULL_FIELD_MASK = (
    "routes.duration,routes.distanceMeters,"
    "routes.polyline.encodedPolyline,routes.localizedValues,"
    "routes.legs.startLocation.latLng,routes.legs.endLocation.latLng,"
    "routes.legs.steps.transitDetails,routes.legs.steps.distanceMeters,"
    "routes.legs.steps.staticDuration,"
    "routes.legs.steps.polyline.encodedPolyline,"
    "routes.legs.steps.navigationInstruction,"
    "routes.legs.steps.localizedValues,routes.legs.steps.travelMode"
)

# Drive summaries: duration/distance/polyline + leg endpoint coordinates for map markers
_DRIVE_FIELD_MASK = (
    "routes.duration,routes.distanceMeters,"
    "routes.polyline.encodedPolyline,routes.localizedValues,"
    "routes.legs.startLocation.latLng,routes.legs.endLocation.latLng"
)


class DriveSummary(TypedDict, total=False):
    duration_text: str | None
    distance_text: str | None
    distance_meters: int | None
    polyline: str | None
    origin_lat_lng: dict[str, float] | None
    destination_lat_lng: dict[str, float] | None


class GoogleMapsRoutesClient:
    """Client for Google Maps Platform Routes API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Google Maps Routes API client.

        Args:
            api_key: Google Maps API key. If not provided, loads from settings.
        """
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.adapter = GoogleMapsSchemaAdapter()
        if not self.api_key:
            logger.warning(
                "GOOGLE_API_KEY not configured - transit routes will be unavailable"
            )

    async def compute_routes(
        self,
        request: TransitRouteRequest,
        field_mask: str = _TRANSIT_FIELD_MASK,
    ) -> TransitRouteResponse:
        """Compute transit routes between origin and destination.

        Args:
            request: Transit route request with origin, destination, and preferences
            field_mask: Google field mask to request. Defaults to the full transit
                mask including leg coordinates.

        Returns:
            TransitRouteResponse with available routes

        Raises:
            TransitRouteError: If the API call fails
        """
        if not self.api_key:
            raise TransitRouteError(
                "Google Maps API key not configured. Set GOOGLE_API_KEY environment variable."
            )

        # Convert domain model to DTO
        dto_request = self.adapter.route_request_to_dto(request)

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask,
        }

        try:
            # Prepare request payload
            request_payload = dto_request.model_dump(exclude_none=True)

            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.debug(
                    f"GOOGLE MAPS API REQUEST URL: {ROUTES_API_URL}",
                    extra={
                        "url": ROUTES_API_URL,
                        "headers": {
                            k: v for k, v in headers.items() if k != "X-Goog-Api-Key"
                        },
                    },
                )
                logger.debug(
                    f"GOOGLE MAPS API REQUEST PAYLOAD: {json.dumps(request_payload, indent=2)}",
                    extra={"request_payload": request_payload},
                )

                # Make API call with DTO (converted to dict)
                response = await client.post(
                    ROUTES_API_URL,
                    json=request_payload,
                    headers=headers,
                )

                # Always log the response, even if there's an error
                response_data = response.json()
                logger.debug(
                    f"GOOGLE MAPS API RESPONSE STATUS: {response.status_code}",
                    extra={"status_code": response.status_code},
                )
                logger.debug(
                    f"GOOGLE MAPS API RESPONSE PAYLOAD:\n{json.dumps(response_data, indent=2)}",
                    extra={"response_payload": response_data},
                )

                # Now check for errors and raise if needed
                response.raise_for_status()

                logger.debug(
                    f"Google Maps Routes API response: {len(response_data.get('routes', []))} routes found"
                )

                # Parse response to DTO
                dto_response = TransitRouteResponseDTO(**response_data)

                # Convert DTO to domain model
                return self.adapter.route_response_from_dto(dto_response)

        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            error_code = None
            error_status = None
            try:
                error_response = e.response.json()
                error_obj = error_response.get("error", {})
                error_detail = error_obj.get("message", str(e))
                error_code = error_obj.get("code")
                error_status = error_obj.get("status")

                # Log full error response for debugging
                logger.error(
                    f"Google Maps Routes API error: {e.response.status_code} - {error_detail}",
                    extra={
                        "status_code": e.response.status_code,
                        "error_code": error_code,
                        "error_status": error_status,
                        "full_error": error_response,
                    },
                )
            except Exception:
                error_detail = e.response.text or str(e)
                logger.error(
                    f"Google Maps Routes API error: {e.response.status_code} - {error_detail}",
                    extra={"status_code": e.response.status_code},
                )

            # Preserve the original error message from Google
            raise TransitRouteError(
                f"Google Maps Routes API error ({e.response.status_code}): {error_detail}"
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Google Maps Routes API request failed: {e}")
            raise TransitRouteError(
                f"Failed to connect to Google Maps Routes API: {e!s}"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error calling Google Maps Routes API: {e}")
            raise TransitRouteError(f"Unexpected error: {e!s}") from e

    async def resolve_drive_summary(
        self, origin: str, destination: str
    ) -> DriveSummary | None:
        """Get drive route summary between two addresses.

        Returns a lightweight dict with duration, distance, polyline, and endpoint
        coordinates. Intended for use by the itinerary travelBars enrichment.

        Args:
            origin: Origin address (e.g., "Eiffel Tower Paris")
            destination: Destination address (e.g., "Louvre Museum Paris")

        Returns:
            Dict with keys: duration_text, distance_text, distance_meters, polyline,
            origin_lat_lng, destination_lat_lng. None if route cannot be computed.
        """
        try:
            request = TransitRouteRequest(
                origin={"address": origin},
                destination={"address": destination},
                travel_mode="DRIVE",
                compute_alternative_routes=False,
            )
            response = await self.compute_routes(request, field_mask=_DRIVE_FIELD_MASK)
            if not response.routes:
                return None

            route = response.routes[0]
            duration_text = None
            distance_text = None
            if route.localized_values:
                duration_text = route.localized_values.duration_text
                distance_text = route.localized_values.distance_text

            origin_lat_lng: dict[str, float] | None = None
            destination_lat_lng: dict[str, float] | None = None
            if route.origin_lat_lng:
                ll = route.origin_lat_lng
                origin_lat_lng = {"lat": ll.latitude, "lng": ll.longitude}
            if route.destination_lat_lng:
                ll = route.destination_lat_lng
                destination_lat_lng = {"lat": ll.latitude, "lng": ll.longitude}

            return {
                "duration_text": duration_text,
                "distance_text": distance_text,
                "distance_meters": route.distance_meters,
                "polyline": route.polyline,
                "origin_lat_lng": origin_lat_lng,
                "destination_lat_lng": destination_lat_lng,
            }
        except Exception as e:
            logger.warning(
                f"resolve_drive_summary failed: {origin!r} → {destination!r} | {e}"
            )
            return None


def get_googlemaps_client() -> GoogleMapsRoutesClient:
    """Get Google Maps Routes API client instance.

    Returns:
        GoogleMapsRoutesClient instance
    """
    return GoogleMapsRoutesClient()
