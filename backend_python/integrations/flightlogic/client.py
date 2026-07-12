"""FlightLogic API client.

Uses adapter/DTO pattern for consistency with SendGrid integration.
"""

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import settings
from app.database.seed.users import TEST_USERS
from app.domains.flight.enums import FlightAPIEnvironment
from app.domains.flight.schemas import (
    AirlineListRequest,
    AirlineListResponse,
    AirportListRequest,
    AirportListResponse,
    FlightBookingRequest,
    FlightBookingResponse,
    FlightCancelRequest,
    FlightCancelResponse,
    FlightExtraServicesRequest,
    FlightExtraServicesResponse,
    FlightFareRulesRequest,
    FlightFareRulesResponse,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    TicketOrderRequest,
    TicketOrderResponse,
    TripDetailsRequest,
    TripDetailsResponse,
)
from app.shared.slack_notify import notify_booking_error

if TYPE_CHECKING:
    from app.domains.hotel.schemas import (
        HotelBookingDetailsRequest,
        HotelBookingDetailsResponse,
        HotelBookingRequest,
        HotelBookingResponse,
        HotelCancelRequest,
        HotelCancelResponse,
        HotelMoreResultsRequest,
        HotelRateRulesRequest,
        HotelRateRulesResponse,
        HotelRoomRatesRequest,
        HotelRoomRatesResponse,
        HotelSearchRequest,
        HotelSearchResponse,
    )
    from app.domains.user import UserPublic

from .adapter import ConversionContext, FlightLogicSchemaAdapter
from .dto import (
    FlightLogicBookingResponse,
    FlightLogicCancelResponse,
    FlightLogicExtraServicesResponse,
    FlightLogicFareRulesResponse,
    FlightLogicRevalidateResponse,
    FlightLogicSearchResponse,
    FlightLogicTicketResponse,
    FlightLogicTripDetailsResponse,
)
from .hotel_adapter import HotelSchemaAdapter
from .hotel_dto import (
    HotelBookingResponseDTO,
    HotelCancelResponseDTO,
    HotelRoomRatesResponseDTO,
    HotelSearchResponseDTO,
)

logger = logging.getLogger(__name__)


def _redact_credentials(data: dict) -> dict:
    """Remove sensitive fields before logging."""
    redacted = data.copy()
    for key in ("user_id", "user_password", "password", "api_key"):
        if key in redacted:
            redacted[key] = "***REDACTED***"
    return redacted


class FlightLogicClient:
    """Client for FlightLogic API operations using adapter/DTO pattern."""

    def __init__(
        self, environment: FlightAPIEnvironment = FlightAPIEnvironment.TEST
    ) -> None:
        """Initialize client with environment-specific configuration."""
        self.environment = environment

        # Flight API URL - use new env var with fallback to deprecated one
        self.base_url = (
            settings.FLIGHTLOGIC_FLIGHTS_API_BASE_URL
            if settings.FLIGHTLOGIC_FLIGHTS_API_BASE_URL
            else (
                settings.FLIGHTLOGIC_API_URL or "https://travelnext.works/api/aeroVE5"
            )
        )

        # Hotel API URL - use new env var
        self.hotel_base_url = settings.FLIGHTLOGIC_HOTELS_API_BASE_URL

        # Revalidate/booking endpoints can take 30-60 seconds
        self.timeout = httpx.Timeout(60.0)
        self.adapter = FlightLogicSchemaAdapter()
        self.hotel_adapter = HotelSchemaAdapter()
        self.logger = logging.getLogger(__name__)

    async def _make_request(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to FlightLogic API with GZIP compression.

        GZIP compression is mandatory for all LIVE traffic per FlightLogic docs.
        """
        import time

        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
        }

        # Add X-Forwarded-For header if spoofing IP is configured (for local dev)
        if settings.FLIGHTLOGIC_SPOOF_IP:
            headers["X-Forwarded-For"] = settings.FLIGHTLOGIC_SPOOF_IP

        # Log basic request info at INFO level
        start_time = time.time()
        logger.info(f"FLIGHTLOGIC FLIGHT REQUEST TO: {url}")

        # Log full payload (redacted) at DEBUG level only
        logger.debug("=" * 80)
        logger.debug(f"FLIGHTLOGIC FLIGHT REQUEST TO: {url}")
        logger.debug("=" * 80)
        logger.debug(
            f"Request Payload:\n{json.dumps(_redact_credentials(data), indent=2, default=str)}"
        )
        logger.debug("=" * 80)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()

                duration_ms = int((time.time() - start_time) * 1000)

                # Check for empty response body (FlightLogic sometimes returns empty on errors)
                if not response.content or not response.content.strip():
                    logger.error(
                        f"← POST {url} | Empty response from FlightLogic | {duration_ms}ms"
                    )
                    raise ValueError(
                        f"FlightLogic returned empty response for {endpoint}. "
                        "The fare may have expired (fares are valid for ~15-20 minutes)."
                    )

                # Parse response
                response_data = response.json()

                # Log basic response info at INFO level
                logger.info(
                    f"FLIGHTLOGIC FLIGHT RESPONSE FROM: {url} | Status: {response.status_code} | Duration: {duration_ms}ms"
                )

                # For availability endpoint: show error on failure, count on success
                if endpoint == "availability":
                    # Check if response indicates failure
                    has_error = False
                    error_msg = None

                    if response_data.get("Errors"):
                        has_error = True
                        errors_obj = response_data["Errors"]
                        if isinstance(errors_obj, dict):
                            error_msg = errors_obj.get("ErrorMessage", "Unknown error")
                        elif isinstance(errors_obj, str):
                            error_msg = errors_obj
                        else:
                            error_msg = str(errors_obj)

                    if has_error:
                        # Log complete error response on failure
                        logger.error("=" * 80)
                        logger.error(f"FLIGHTLOGIC FLIGHT ERROR RESPONSE FROM: {url}")
                        logger.error(
                            f"Status: {response.status_code} | Duration: {duration_ms}ms"
                        )
                        logger.error("=" * 80)
                        logger.error(f"Error Message: {error_msg}")
                        logger.error("=" * 80)
                        logger.error(
                            f"Error Response Payload:\n{json.dumps(_redact_credentials(response_data), indent=2, default=str)}"
                        )
                        logger.error("=" * 80)
                    else:
                        # Log only count on success
                        fare_count = 0
                        if response_data.get("AirSearchResponse"):
                            air_search = response_data["AirSearchResponse"]
                            if air_search.get("AirSearchResult"):
                                fare_itineraries = (
                                    air_search["AirSearchResult"].get("FareItineraries")
                                    or []
                                )
                                fare_count = len(fare_itineraries)
                        logger.info(
                            f"✅ Flight search successful: {fare_count} flights found"
                        )
                elif endpoint == "airport_list":
                    logger.debug(
                        f"Response payload hidden for {endpoint} endpoint (large airport list) to keep logs manageable"
                    )
                elif endpoint == "airline_list":
                    airline_count = (
                        len(response_data) if isinstance(response_data, list) else 0
                    )
                    logger.info(
                        f"FLIGHTLOGIC AIRLINE_LIST: {response.status_code} | {duration_ms}ms | {airline_count} airlines"
                    )
                    logger.debug(
                        f"FLIGHTLOGIC AIRLINE_LIST REQUEST:\n{json.dumps(_redact_credentials(data), indent=2, default=str)}"
                    )
                    logger.debug(
                        f"FLIGHTLOGIC AIRLINE_LIST RESPONSE:\n{json.dumps(_redact_credentials(response_data), indent=2, default=str)}"
                    )
                else:
                    # Log full payload (redacted) at DEBUG level only for other endpoints
                    logger.debug("=" * 80)
                    logger.debug(f"FLIGHTLOGIC FLIGHT RESPONSE FROM: {url}")
                    logger.debug(
                        f"Status: {response.status_code} | Duration: {duration_ms}ms"
                    )
                    logger.debug("=" * 80)
                    logger.debug(
                        f"Response Payload:\n{json.dumps(_redact_credentials(response_data), indent=2, default=str)}"
                    )
                    logger.debug("=" * 80)

                return response_data
            except httpx.HTTPError as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"← POST {url} | FlightLogic API error | {duration_ms}ms: {e}"
                )
                raise
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"← POST {url} | Unexpected error | {duration_ms}ms: {e}")
                raise

    async def search_flights(
        self, request: FlightSearchRequest
    ) -> FlightSearchResponse:
        """Search for available flights."""
        # Convert domain model to DTO
        dto_request = self.adapter.search_request_to_dto(request)

        # Make API call
        response_data = await self._make_request(
            "availability", dto_request.model_dump(by_alias=True)
        )

        # Log response summary
        fare_count = 0
        if response_data.get("AirSearchResponse"):
            air_search = response_data["AirSearchResponse"]
            if air_search.get("AirSearchResult"):
                fare_itineraries = (
                    air_search["AirSearchResult"].get("FareItineraries") or []
                )
                fare_count = len(fare_itineraries)

        # Only log errors or zero results (success case handled by FlightService)
        if fare_count == 0:
            if response_data.get("Errors"):
                error_msg = response_data["Errors"].get(
                    "ErrorMessage", "No data available"
                )
                logger.warning(f"Flight search error: {error_msg}")
            else:
                logger.debug("Search completed with no results")

        # Parse response to DTO
        dto_response = FlightLogicSearchResponse(**response_data)

        # Convert DTO to domain model
        return self.adapter.search_response_from_dto(dto_response)

    async def revalidate_fare(
        self, request: FlightRevalidateRequest
    ) -> FlightRevalidateResponse:
        """Revalidate a selected fare."""
        # Convert domain model to DTO
        dto_request = self.adapter.revalidate_request_to_dto(request)

        # Make API call
        response_data = await self._make_request(
            "revalidate", dto_request.model_dump(by_alias=True)
        )

        # Log only errors (success case handled by FlightService)
        if response_data.get("Errors"):
            error_msg = response_data["Errors"].get("ErrorMessage", "Unknown")
            logger.warning(f"Revalidate API error: {error_msg}")

        # Parse response to DTO
        dto_response = FlightLogicRevalidateResponse(**response_data)

        # Create context with request information
        context = ConversionContext(
            session_id=request.session_id,
            fare_source_code=request.fare_source_code,
            inbound_fare_source_code=request.return_fare_source_code,
        )

        # Convert DTO to domain model with context
        return self.adapter.revalidate_response_from_dto(dto_response, context)

    async def create_booking(
        self, request: FlightBookingRequest
    ) -> FlightBookingResponse:
        """Create a flight booking."""
        try:
            # Convert domain model to DTO
            dto_request = self.adapter.booking_request_to_dto(request)

            request_data = dto_request.model_dump(by_alias=True)

            # Log booking request for debugging
            logger.info("=" * 80)
            logger.info("FLIGHTLOGIC BOOKING REQUEST:")
            logger.info("=" * 80)
            logger.info(f"Adults: {len(request.passenger_groups.adults or [])}")
            logger.info(f"Children: {len(request.passenger_groups.children or [])}")
            logger.info(f"Infants: {len(request.passenger_groups.infants or [])}")
            # Check the correct path for PaxDetails
            pax_details = request_data.get("paxInfo", {}).get("paxDetails", [])
            logger.info(f"PaxDetails count in DTO: {len(pax_details)}")
            logger.info(f"Full request_data keys: {request_data.keys()}")

            # CRITICAL DEBUG: Log flightBookingInfo to see what's being sent
            flight_booking_info = request_data.get("flightBookingInfo", {})
            logger.info(f"flightBookingInfo keys: {list(flight_booking_info.keys())}")
            logger.info(
                f"flight_session_id: {flight_booking_info.get('flight_session_id')}"
            )
            logger.info(
                f"fare_source_code: {flight_booking_info.get('fare_source_code')}"
            )

            logger.info(f"paxInfo: {request_data.get('paxInfo', {})}")
            logger.info("=" * 80)

            # Log essential request info only (reduced verbosity)
            logger.info(
                f"FlightLogic booking request - Passengers: {len(pax_details)}, Fare: {flight_booking_info.get('fare_source_code', 'N/A')[:10] if flight_booking_info.get('fare_source_code') else 'N/A'}..."
            )

            # Make API call
            response_data = await self._make_request("booking", request_data)

            # Log essential response info only (reduced verbosity)
            booking_status = response_data.get("AirBookingResponse", {}).get(
                "BookingStatus", "UNKNOWN"
            )
            unique_id = response_data.get("AirBookingResponse", {}).get(
                "UniqueID", "N/A"
            )[:15]
            logger.info(
                f"FlightLogic booking response - Status: {booking_status}, ID: {unique_id}..."
            )

            # Parse response to DTO
            try:
                dto_response = FlightLogicBookingResponse(**response_data)
            except Exception as e:
                logger.error(f"Failed to parse booking response: {e}")
                raise

            # Convert DTO to domain model
            result = self.adapter.booking_response_from_dto(dto_response)
            if not result.is_successful:
                error_msg = (
                    result.errors[0].message if result.errors else "Unknown error"
                )
                await notify_booking_error(
                    "Flight Booking API",
                    error_msg,
                    context={"flight_session_id": request.session_id},
                )
            return result
        except Exception as e:
            await notify_booking_error(
                "Flight Booking API",
                str(e),
                context={"flight_session_id": getattr(request, "session_id", None)},
            )
            raise

    async def create_booking_with_payload(
        self, payload: dict[str, Any]
    ) -> FlightBookingResponse:
        """Create a flight booking using a pre-serialized payload (for admin LCC retry).

        The payload must be the exact dict sent to FlightLogic (e.g. stored in booking event).
        """
        response_data = await self._make_request("booking", payload)
        try:
            dto_response = FlightLogicBookingResponse(**response_data)
        except Exception as e:
            logger.error("Failed to parse booking response: %s", e)
            raise
        return self.adapter.booking_response_from_dto(dto_response)

    async def issue_tickets(self, request: TicketOrderRequest) -> TicketOrderResponse:
        """Issue tickets for a booking."""
        try:
            # Convert domain model to DTO
            dto_request = self.adapter.ticket_request_to_dto(request)

            # Make API call
            response_data = await self._make_request(
                "ticket_order", dto_request.model_dump(by_alias=True)
            )

            # Parse response to DTO
            dto_response = FlightLogicTicketResponse(**response_data)

            # Convert DTO to domain model
            result = self.adapter.ticket_response_from_dto(dto_response)
            if not result.success or result.errors:
                error_msg = (
                    result.errors[0].message if result.errors else "Unknown error"
                )
                unique_id = (
                    request.external_booking_reference or request.voya_booking_reference
                )
                await notify_booking_error(
                    "Flight Ticket Order API",
                    error_msg,
                    context={"UniqueID": unique_id},
                )
            return result
        except Exception as e:
            unique_id = (
                request.external_booking_reference or request.voya_booking_reference
            )
            await notify_booking_error(
                "Flight Ticket Order API",
                str(e),
                context={"UniqueID": unique_id},
            )
            raise

    async def cancel_booking(
        self, request: FlightCancelRequest
    ) -> FlightCancelResponse:
        """Cancel a booking."""
        # Convert domain model to DTO
        dto_request = self.adapter.cancel_request_to_dto(request)

        # Make API call
        response_data = await self._make_request(
            "cancel", dto_request.model_dump(by_alias=True)
        )

        # Parse response to DTO
        dto_response = FlightLogicCancelResponse(**response_data)

        # Convert DTO to domain model
        return self.adapter.cancel_response_from_dto(dto_response)

    async def get_fare_rules(
        self, request: FlightFareRulesRequest
    ) -> FlightFareRulesResponse:
        """Get fare rules and restrictions."""
        # Convert domain model to DTO
        dto_request = self.adapter.fare_rules_request_to_dto(request)

        # Make API call
        response_data = await self._make_request(
            "fare_rules", dto_request.model_dump(by_alias=True)
        )

        # Parse response to DTO
        dto_response = FlightLogicFareRulesResponse(**response_data)

        # Convert DTO to domain model
        return self.adapter.fare_rules_response_from_dto(dto_response)

    async def get_extra_services(
        self, request: FlightExtraServicesRequest
    ) -> FlightExtraServicesResponse:
        """Get available extra services."""
        # Convert domain model to DTO
        dto_request = self.adapter.extra_services_request_to_dto(request)

        # Make API call
        response_data = await self._make_request(
            "extra_services", dto_request.model_dump(by_alias=True)
        )

        # Parse response to DTO
        dto_response = FlightLogicExtraServicesResponse(**response_data)

        # Convert DTO to domain model
        return self.adapter.extra_services_response_from_dto(dto_response)

    async def get_trip_details(
        self, request: TripDetailsRequest
    ) -> TripDetailsResponse:
        """Get trip/booking details."""
        # Convert domain model to DTO
        dto_request = self.adapter.trip_details_request_to_dto(request)

        # Make API call
        response_data = await self._make_request(
            "trip_details", dto_request.model_dump(by_alias=True)
        )

        # Log essential trip details info only (reduced verbosity)
        trip_response = response_data.get("AirTripDetailsResponse", {})
        unique_id = trip_response.get("UniqueID", "N/A")[:15]
        segments_count = len(
            trip_response.get("TripDetailsResult", {}).get("Segments", [])
        )
        logger.info(
            f"FlightLogic trip details - ID: {unique_id}..., Segments: {segments_count}"
        )

        # Parse response to DTO
        dto_response = FlightLogicTripDetailsResponse(**response_data)

        # Convert DTO to domain model
        return self.adapter.trip_details_response_from_dto(dto_response)

    # ============================================================
    # HOTEL API v6 METHODS
    # ============================================================

    async def _make_hotel_request(
        self, endpoint: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Make HTTP request to FlightLogic Hotel API v6 with GZIP compression.

        GZIP compression is mandatory for all LIVE traffic per FlightLogic docs.
        """
        import time

        url = f"{self.hotel_base_url}/{endpoint}"
        headers = {
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
        }

        # Add X-Forwarded-For header if spoofing IP is configured (for local dev)
        if settings.FLIGHTLOGIC_SPOOF_IP:
            headers["X-Forwarded-For"] = settings.FLIGHTLOGIC_SPOOF_IP

        # Log basic request info at INFO level
        start_time = time.time()
        logger.info(f"FLIGHTLOGIC HOTEL REQUEST TO: {url}")

        # Log full payload (redacted) at DEBUG level only
        logger.debug("=" * 80)
        logger.debug(f"FLIGHTLOGIC HOTEL REQUEST TO: {url}")
        logger.debug("=" * 80)
        logger.debug(
            f"Request Payload:\n{json.dumps(_redact_credentials(data), indent=2, default=str)}"
        )
        logger.debug("=" * 80)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()

                duration_ms = int((time.time() - start_time) * 1000)

                # Check for empty response body (FlightLogic sometimes returns empty on errors)
                if not response.content or not response.content.strip():
                    logger.error(
                        f"← POST {url} | Empty response from FlightLogic Hotel API | {duration_ms}ms"
                    )
                    raise ValueError(
                        f"FlightLogic returned empty response for {endpoint}. "
                        "The rate may have expired (rates are valid for ~15-20 minutes)."
                    )

                # Parse response
                response_data = response.json()

                # Log basic response info at INFO level
                logger.info(
                    f"FLIGHTLOGIC HOTEL RESPONSE FROM: {url} | Status: {response.status_code} | Duration: {duration_ms}ms"
                )

                # For hotel_search and get_room_rates: show full response on error, count only on success
                if endpoint in ("hotel_search", "get_room_rates"):
                    # Check if response indicates failure
                    has_error = False
                    status = response_data.get("status", {})

                    # Check various error formats
                    if isinstance(status, dict) and (
                        status.get("error")
                        or (
                            isinstance(status.get("errors"), list)
                            and len(status.get("errors", [])) > 0
                        )
                    ):
                        has_error = True
                    if response_data.get("errors"):
                        has_error = True

                    if has_error:
                        # Log full response payload on error for debugging
                        logger.error("=" * 80)
                        logger.error(f"FLIGHTLOGIC HOTEL ERROR RESPONSE FROM: {url}")
                        logger.error(
                            f"Status: {response.status_code} | Duration: {duration_ms}ms"
                        )
                        logger.error("=" * 80)
                        logger.error(
                            f"Error Response Payload:\n{json.dumps(_redact_credentials(response_data), indent=2, default=str)}"
                        )
                        logger.error("=" * 80)
                    elif endpoint == "hotel_search":
                        # Log only count on success
                        hotel_count = 0
                        if isinstance(status, dict):
                            hotel_count = status.get("totalResults", 0)
                        logger.info(
                            f"✅ Hotel search successful: {hotel_count} hotels found"
                        )
                    elif endpoint == "get_room_rates":
                        # Log only count on success
                        room_count = 0
                        room_rates = response_data.get("roomRates", {})
                        if isinstance(room_rates, dict):
                            per_booking_rates = room_rates.get("perBookingRates", [])
                            if isinstance(per_booking_rates, list):
                                room_count = len(per_booking_rates)
                        logger.info(
                            f"✅ Room rates successful: {room_count} room options found"
                        )
                else:
                    # Log full payload (redacted) at DEBUG level only for other endpoints
                    logger.debug("=" * 80)
                    logger.debug(f"FLIGHTLOGIC HOTEL RESPONSE FROM: {url}")
                    logger.debug(
                        f"Status: {response.status_code} | Duration: {duration_ms}ms"
                    )
                    logger.debug("=" * 80)
                    logger.debug(
                        f"Response Payload:\n{json.dumps(_redact_credentials(response_data), indent=2, default=str)}"
                    )
                    logger.debug("=" * 80)

                return response_data
            except httpx.HTTPError as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"← POST {url} | FlightLogic Hotel API error | {duration_ms}ms: {e}"
                )
                raise
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"← POST {url} | Unexpected error | {duration_ms}ms: {e}")
                raise

    async def _make_hotel_get_request(
        self, endpoint: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Make GET HTTP request to FlightLogic Hotel API v6 with GZIP compression.

        Used for endpoints that require GET with query parameters (e.g., moreResults).

        Args:
            endpoint: API endpoint path
            params: Query parameters as dictionary

        Returns:
            Response data as dictionary
        """
        import time

        url = f"{self.hotel_base_url}/{endpoint}"
        headers = {
            "Accept-Encoding": "gzip",
        }

        # Add X-Forwarded-For header if spoofing IP is configured (for local dev)
        if settings.FLIGHTLOGIC_SPOOF_IP:
            headers["X-Forwarded-For"] = settings.FLIGHTLOGIC_SPOOF_IP

        # Log basic request info at INFO level
        start_time = time.time()
        logger.info(f"FLIGHTLOGIC HOTEL GET REQUEST TO: {url}")

        # Log full payload (redacted) at DEBUG level only
        logger.debug("=" * 80)
        logger.debug(f"FLIGHTLOGIC HOTEL GET REQUEST TO: {url}")
        logger.debug("=" * 80)
        logger.debug(
            f"Query Parameters:\n{json.dumps(_redact_credentials(params), indent=2, default=str)}"
        )
        logger.debug("=" * 80)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()

                duration_ms = int((time.time() - start_time) * 1000)

                # Check for empty response body
                if not response.content or not response.content.strip():
                    logger.error(
                        f"← GET {url} | Empty response from FlightLogic Hotel API | {duration_ms}ms"
                    )
                    raise ValueError(
                        f"FlightLogic returned empty response for {endpoint}."
                    )

                # Parse response
                response_data = response.json()

                # Log basic response info at INFO level
                logger.info(
                    f"FLIGHTLOGIC HOTEL GET RESPONSE FROM: {url} | Status: {response.status_code} | Duration: {duration_ms}ms"
                )

                # Log full payload (redacted) at DEBUG level only
                logger.debug("=" * 80)
                logger.debug(f"FLIGHTLOGIC HOTEL GET RESPONSE FROM: {url}")
                logger.debug(
                    f"Status: {response.status_code} | Duration: {duration_ms}ms"
                )
                logger.debug("=" * 80)
                logger.debug(
                    f"Response Payload:\n{json.dumps(_redact_credentials(response_data), indent=2, default=str)}"
                )
                logger.debug("=" * 80)

                return response_data
            except httpx.HTTPError as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(
                    f"← GET {url} | FlightLogic Hotel API error | {duration_ms}ms: {e}"
                )
                raise
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"← GET {url} | Unexpected error | {duration_ms}ms: {e}")
                raise

    async def search_hotels(
        self, request: "HotelSearchRequest"
    ) -> "HotelSearchResponse":
        """Search for available hotels.

        Args:
            request: Hotel search request from domain layer

        Returns:
            Hotel search response with available hotels
        """
        # Convert domain model to DTO
        dto_request = self.hotel_adapter.search_request_to_dto(request)

        # Make API call
        response_data = await self._make_hotel_request(
            "hotel_search", dto_request.model_dump(by_alias=True, exclude_none=True)
        )

        # Try to parse response to DTO - if it fails, extract error from raw response
        try:
            dto_response = HotelSearchResponseDTO(**response_data)
        except Exception as parse_error:
            # Parsing failed - likely an error response from FlightLogic
            # Extract error information from raw response_data
            from app.domains.hotel.exceptions import HotelSearchError

            # Try to extract error messages from response
            error_messages = []
            status = response_data.get("status", {})

            # Check various error formats in the response
            if isinstance(status, dict):
                # Check for errors array
                if "errors" in status and isinstance(status["errors"], list):
                    for error_item in status["errors"]:
                        if (
                            isinstance(error_item, dict)
                            and "errorMessage" in error_item
                        ):
                            error_messages.append(error_item["errorMessage"])
                # Check for singular error
                elif "error" in status:
                    error_val = status["error"]
                    if isinstance(error_val, str):
                        error_messages.append(error_val)

            # Join error messages or use fallback
            if error_messages:
                error_msg = ", ".join(error_messages)
            else:
                # Fallback: use parse error message
                error_msg = str(parse_error)

            logger.warning(f"Hotel search error from FlightLogic: {error_msg}")
            raise HotelSearchError(reason=error_msg) from parse_error

        # Log response summary
        hotel_count = 0
        if response_data.get("status"):
            hotel_count = response_data["status"].get("totalResults", 0)

        # Only log errors or zero results
        if hotel_count == 0:
            if response_data.get("errors"):
                error_msg = response_data["errors"].get(
                    "errorMessage", "No hotels available"
                )
                logger.warning(f"Hotel search error: {error_msg}")
            else:
                logger.debug("Hotel search completed with no results")

        # Convert DTO to domain model
        return self.hotel_adapter.search_response_from_dto(dto_response)

    async def get_more_results(
        self, request: "HotelMoreResultsRequest"
    ) -> "HotelSearchResponse":
        """Get additional hotel search results using pagination token.

        Args:
            request: More results request with session ID and next token

        Returns:
            Hotel search response with additional results
        """
        # Convert domain model to DTO
        dto_request = self.hotel_adapter.more_results_request_to_dto(request)

        # Make GET API call with query parameters
        response_data = await self._make_hotel_get_request(
            "moreResults", dto_request.model_dump(by_alias=True, exclude_none=True)
        )

        # Check for error response from FlightLogic before parsing
        if response_data.get("status") and isinstance(response_data["status"], dict):
            error_msg = response_data["status"].get("error")
            if error_msg:
                from app.domains.hotel.exceptions import HotelSearchError

                logger.warning(f"More results error from FlightLogic: {error_msg}")
                raise HotelSearchError(reason=error_msg)

        # Log response summary
        hotel_count = 0
        if response_data.get("status"):
            hotel_count = response_data["status"].get("totalResults", 0)

        # Only log errors or zero results
        if hotel_count == 0:
            if response_data.get("errors"):
                error_msg = response_data["errors"].get(
                    "errorMessage", "No more hotels available"
                )
                logger.warning(f"More results error: {error_msg}")
            else:
                logger.debug("More results completed with no results")

        # Parse response to DTO (uses dedicated HotelMoreResultsResponseDTO)
        from .hotel_dto import HotelMoreResultsResponseDTO

        dto_response = HotelMoreResultsResponseDTO(**response_data)

        # Convert DTO to domain model
        return self.hotel_adapter.more_results_response_from_dto(dto_response)

    async def get_room_rates(
        self, request: "HotelRoomRatesRequest"
    ) -> "HotelRoomRatesResponse":
        """Get detailed room rates for a specific hotel.

        Args:
            request: Room rates request with session ID and token ID

        Returns:
            Available room options with pricing details
        """
        # Convert domain model to DTO
        dto_request = self.hotel_adapter.room_rates_request_to_dto(request)

        # Debug logging
        logger.info(
            f"Room rates request: session_id={request.session_id[:20]}..., "
            f"token_id={request.token_id}"
        )

        # Make API call
        response_data = await self._make_hotel_request(
            "get_room_rates", dto_request.model_dump(by_alias=True, exclude_none=True)
        )

        # Try to parse response to DTO - if it fails, extract error from raw response
        try:
            dto_response = HotelRoomRatesResponseDTO(**response_data)
        except Exception as parse_error:
            # Parsing failed - likely an error response from FlightLogic
            # Extract error information from raw response_data
            from app.domains.hotel.exceptions import HotelSearchError

            # Try to extract error messages from response
            error_messages = []
            status = response_data.get("status", {})

            # Check various error formats in the response
            if isinstance(status, dict):
                # Check for errors array
                if "errors" in status and isinstance(status["errors"], list):
                    for error_item in status["errors"]:
                        if (
                            isinstance(error_item, dict)
                            and "errorMessage" in error_item
                        ):
                            error_messages.append(error_item["errorMessage"])
                # Check for singular error
                elif "error" in status:
                    error_val = status["error"]
                    if isinstance(error_val, str):
                        error_messages.append(error_val)

            # Check for top-level errors
            if response_data.get("errors"):
                errors_obj = response_data["errors"]
                if isinstance(errors_obj, dict) and "errorMessage" in errors_obj:
                    error_messages.append(errors_obj["errorMessage"])

            # Join error messages or use fallback
            if error_messages:
                error_msg = ", ".join(error_messages)
            else:
                # Fallback: use parse error message
                error_msg = str(parse_error)

            logger.warning(f"Room rates error from FlightLogic: {error_msg}")
            raise HotelSearchError(reason=error_msg) from parse_error

        # Convert DTO to domain model
        return self.hotel_adapter.room_rates_response_from_dto(dto_response)

    async def book_hotel(
        self, request: "HotelBookingRequest"
    ) -> "HotelBookingResponse":
        """Create a hotel booking.

        Args:
            request: Hotel booking request with guest and payment details

        Returns:
            Booking confirmation or error details
        """
        try:
            # Convert domain model to DTO
            dto_request = self.hotel_adapter.booking_request_to_dto(request)

            # Log booking request for debugging
            request_data = dto_request.model_dump(by_alias=True, exclude_none=True)
            logger.info("=" * 80)
            logger.info("FLIGHTLOGIC HOTEL BOOKING REQUEST:")
            logger.info("=" * 80)
            logger.info(f"Session ID: {request.session_id}")
            logger.info(f"Rate Basis ID: {request.rate_basis_id}")
            logger.info(f"Product ID: {request.product_id}")
            logger.info(f"Client Ref: {request.client_ref}")
            if request.guests and len(request.guests) > 0:
                first_guest = request.guests[0]
                logger.info(
                    f"Primary Guest: {first_guest.title} {first_guest.first_name} {first_guest.last_name}"
                )
            logger.info(f"Total Guests: {len(request.guests)}")
            logger.info("=" * 80)

            # Log full request payload in Test mode for debugging (redacted)
            if self.environment.value == "Test":
                logger.debug("Full request payload:")
                logger.debug(json.dumps(_redact_credentials(request_data), indent=2))

            # Make API call (endpoint is "hotel_book" not "hotel_booking")
            response_data = await self._make_hotel_request("hotel_book", request_data)

            # Log essential response info (handle both success and error responses)
            status = response_data.get("status", "UNKNOWN")
            # Handle error response where status is a dict
            if isinstance(status, dict):
                status_str = f"ERROR: {status.get('error', 'Unknown error')}"
            else:
                status_str = status
            confirmation_num = str(response_data.get("supplierConfirmationNum", "N/A"))[
                :15
            ]
            logger.info(
                f"FlightLogic hotel booking response - Status: {status_str}, Confirmation: {confirmation_num}"
            )

            # Log full response for debugging (only in Test environment, redacted)
            if self.environment.value == "Test":
                logger.debug("Full booking response:")
                logger.debug(json.dumps(_redact_credentials(response_data), indent=2))

            # Parse response to DTO
            try:
                dto_response = HotelBookingResponseDTO(**response_data)
            except Exception as e:
                logger.error(f"Failed to parse hotel booking response: {e}")
                raise

            # Convert DTO to domain model
            response = self.hotel_adapter.booking_response_from_dto(dto_response)
            if response.status == "Failed" or response.errors:
                error_msg = (
                    response.errors.get("message", "Unknown error")
                    if response.errors
                    else "Booking failed"
                )
                await notify_booking_error(
                    "Hotel Booking API",
                    error_msg,
                    context={
                        "sessionId": request.session_id,
                        "productId": request.product_id,
                        "tokenId": request.token_id,
                        "rateBasisId": request.rate_basis_id,
                    },
                )
            return response
        except Exception as e:
            await notify_booking_error(
                "Hotel Booking API",
                str(e),
                context={
                    "sessionId": getattr(request, "session_id", None),
                    "productId": getattr(request, "product_id", None),
                    "tokenId": getattr(request, "token_id", None),
                    "rateBasisId": getattr(request, "rate_basis_id", None),
                },
            )
            raise

    async def book_hotel_with_payload(
        self, payload: dict[str, Any]
    ) -> "HotelBookingResponse":
        """Create a hotel booking using a pre-serialized payload (for admin retry).

        The payload must be the exact dict sent to FlightLogic (e.g. stored in booking event).
        """
        response_data = await self._make_hotel_request("hotel_book", payload)
        try:
            dto_response = HotelBookingResponseDTO(**response_data)
        except Exception as e:
            logger.error("Failed to parse hotel booking response: %s", e)
            raise
        return self.hotel_adapter.booking_response_from_dto(dto_response)

    async def check_rate_rules(
        self, request: "HotelRateRulesRequest"
    ) -> "HotelRateRulesResponse":
        """Check and validate hotel rate rules before booking.

        This should be called before booking to ensure rates are still valid.

        Args:
            request: Rate rules request with session and rate identifiers

        Returns:
            Validated rate information
        """
        # Convert domain model to DTO
        dto_request = self.hotel_adapter.rate_rules_request_to_dto(request)

        # Make API call
        response_data = await self._make_hotel_request(
            "get_rate_rules", dto_request.model_dump(by_alias=True, exclude_none=True)
        )

        # Log only errors
        if response_data.get("errors"):
            error_msg = response_data["errors"].get("errorMessage", "Unknown")
            logger.warning(f"Rate rules API error: {error_msg}")

        # Parse response to DTO
        from .hotel_dto import HotelRateRulesResponseDTO

        dto_response = HotelRateRulesResponseDTO(**response_data)

        # Convert DTO to domain model
        return self.hotel_adapter.rate_rules_response_from_dto(dto_response)

    async def cancel_hotel_booking(
        self, request: "HotelCancelRequest"
    ) -> "HotelCancelResponse":
        """Cancel a hotel booking.

        Args:
            request: Cancel request with supplier confirmation and reference numbers

        Returns:
            Cancellation confirmation or error details
        """
        # Convert domain model to DTO
        dto_request = self.hotel_adapter.cancel_request_to_dto(request)

        # Log cancellation request for debugging
        request_data = dto_request.model_dump(by_alias=True, exclude_none=True)
        logger.info("=" * 80)
        logger.info("FLIGHTLOGIC HOTEL CANCELLATION REQUEST:")
        logger.info("=" * 80)
        logger.info(f"Supplier Confirmation: {request.supplier_confirmation_num}")
        logger.info(f"Reference Number: {request.reference_num}")
        logger.info("=" * 80)

        # Make API call (endpoint is "cancel" per documentation)
        response_data = await self._make_hotel_request("cancel", request_data)

        # Log essential response info
        status = response_data.get("status", "UNKNOWN")
        cancel_ref = response_data.get("cancelReferenceNum", "N/A")
        logger.info(
            f"FlightLogic hotel cancellation response - Status: {status}, Cancel Ref: {cancel_ref}"
        )

        # Parse response to DTO
        try:
            dto_response = HotelCancelResponseDTO(**response_data)
        except Exception as e:
            logger.error(f"Failed to parse hotel cancellation response: {e}")
            raise

        # Convert DTO to domain model
        return self.hotel_adapter.cancel_response_from_dto(dto_response)

    async def get_booking_details(
        self, request: "HotelBookingDetailsRequest"
    ) -> "HotelBookingDetailsResponse":
        """Get complete hotel booking details.

        Args:
            request: Booking details request with supplier confirmation and reference numbers

        Returns:
            Complete booking details or error information
        """
        # Convert domain model to DTO
        dto_request = self.hotel_adapter.booking_details_request_to_dto(request)

        # Make API call (endpoint is "bookingDetails" per documentation)
        response_data = await self._make_hotel_request(
            "bookingDetails", dto_request.model_dump(by_alias=True, exclude_none=True)
        )

        # Check for error response from FlightLogic before parsing
        if response_data.get("errors"):
            error_msg = response_data["errors"].get("errorMessage", "Unknown error")
            from app.domains.hotel.exceptions import HotelBookingError

            logger.warning(f"Booking details error from FlightLogic: {error_msg}")
            raise HotelBookingError(reason=error_msg)

        # Handle error field (singular) vs errors (plural)
        error_value = response_data.get("error")
        if error_value and error_value != "":
            error_msg = (
                str(error_value) if isinstance(error_value, str) else "Unknown error"
            )
            from app.domains.hotel.exceptions import HotelBookingError

            logger.warning(f"Booking details error from FlightLogic: {error_msg}")
            raise HotelBookingError(reason=error_msg)

        # Handle status.error (FlightLogic bookingDetails returns "Booking Not Found" in status object with HTTP 200)
        status_obj = response_data.get("status")
        if isinstance(status_obj, dict) and status_obj.get("error"):
            status_error = status_obj["error"]
            error_msg = (
                str(status_error).strip()
                if isinstance(status_error, str) and str(status_error).strip()
                else None
            )
            if error_msg:
                from app.domains.hotel.exceptions import HotelBookingError

                logger.warning(f"Booking details error from FlightLogic: {error_msg}")
                raise HotelBookingError(reason=error_msg)

        # Parse response to DTO
        from .hotel_dto import HotelBookingDetailsResponseDTO

        dto_response = HotelBookingDetailsResponseDTO(**response_data)

        # Convert DTO to domain model
        return self.hotel_adapter.booking_details_response_from_dto(dto_response)

    async def get_airport_list(
        self, _request: AirportListRequest
    ) -> AirportListResponse:
        """Get list of commercial airports from FlightLogic.

        Returns a curated list of commercial airports, excluding private
        and military airports.

        Args:
            request: Airport list request

        Returns:
            Airport list response with commercial airports
        """
        from .dto import AirportListItemDTO, FlightLogicAirportListRequest

        # Build DTO request
        dto_request = FlightLogicAirportListRequest(
            user_id=settings.FLIGHTLOGIC_USER_ID,
            user_password=settings.FLIGHTLOGIC_PASSWORD,
            access=self.environment.value,
            ip_address=settings.FLIGHTLOGIC_IP_ADDRESS,
        )

        # Make API call
        request_data = dto_request.model_dump(by_alias=True, exclude_none=True)
        logger.info("Fetching airport list from FlightLogic")
        logger.debug(
            f"Airport list request:\n{json.dumps(_redact_credentials(request_data), indent=2)}"
        )

        response_data = await self._make_request("airport_list", request_data)

        # Check for errors
        if isinstance(response_data, dict) and "Errors" in response_data:
            errors = response_data["Errors"]
            error_code = errors.get("ErrorCode", "UNKNOWN")
            error_message = errors.get("ErrorMessage", "Unknown error")
            logger.error(
                f"FlightLogic airport list error: {error_code} - {error_message}"
            )
            from app.domains.flight.exceptions import FlightSearchError

            raise FlightSearchError(
                reason=f"Airport list request failed: {error_message}"
            )

        # Parse response - can be list or dict
        if isinstance(response_data, list):
            # Success: list of airports
            airport_items = [AirportListItemDTO(**airport) for airport in response_data]
        elif isinstance(response_data, dict) and "Errors" in response_data:
            # Error response
            errors = response_data["Errors"]
            error_code = errors.get("ErrorCode", "UNKNOWN")
            error_message = errors.get("ErrorMessage", "Unknown error")
            logger.error(
                f"FlightLogic airport list error: {error_code} - {error_message}"
            )
            from app.domains.flight.exceptions import FlightSearchError

            raise FlightSearchError(
                reason=f"Airport list request failed: {error_message}"
            )
        else:
            logger.error(
                f"Unexpected airport list response format: {type(response_data)}"
            )
            from app.domains.flight.exceptions import FlightSearchError

            raise FlightSearchError(reason="Unexpected airport list response format")

        # Convert DTO to domain model
        from app.domains.flight.schemas import AirportListItem

        airport_list_items = [
            AirportListItem(
                iata_code=item.AirportCode,
                airport_name=item.AirportName,
                city=item.City,
                country=item.Country,
            )
            for item in airport_items
        ]

        return AirportListResponse(airports=airport_list_items)

    async def get_airline_list(
        self, _request: AirlineListRequest
    ) -> AirlineListResponse:
        """Get list of airlines with logos from FlightLogic.

        Returns airlines supported by the API with codes, names, and logo URLs.
        Used internally to enrich flight search results with airline logos.

        Args:
            request: Airline list request

        Returns:
            Airline list response with airlines (iata_code, name, logo_url)
        """
        from .dto import AirlineListItemDTO, FlightLogicAirlineListRequest

        # Build DTO request (same params as airport_list)
        dto_request = FlightLogicAirlineListRequest(
            user_id=settings.FLIGHTLOGIC_USER_ID,
            user_password=settings.FLIGHTLOGIC_PASSWORD,
            access=self.environment.value,
            ip_address=settings.FLIGHTLOGIC_IP_ADDRESS,
        )

        # Make API call (request/response logged at INFO in _make_request)
        request_data = dto_request.model_dump(by_alias=True, exclude_none=True)
        response_data = await self._make_request("airline_list", request_data)

        # Check for errors
        if isinstance(response_data, dict) and "Errors" in response_data:
            errors = response_data["Errors"]
            error_code = errors.get("ErrorCode", "UNKNOWN")
            error_message = errors.get("ErrorMessage", "Unknown error")
            logger.error(
                f"FlightLogic airline list error: {error_code} - {error_message}"
            )
            from app.domains.flight.exceptions import FlightSearchError

            raise FlightSearchError(
                reason=f"Airline list request failed: {error_message}"
            )

        # Parse response - success is a list
        if isinstance(response_data, list):
            airline_items = [AirlineListItemDTO(**item) for item in response_data]
        else:
            logger.error(
                f"Unexpected airline list response format: {type(response_data)}"
            )
            from app.domains.flight.exceptions import FlightSearchError

            raise FlightSearchError(reason="Unexpected airline list response format")

        # Convert DTO to domain model
        from app.domains.flight.schemas import AirlineListItem

        airline_list_items = [
            AirlineListItem(
                iata_code=item.AirLineCode,
                name=item.AirLineName,
                logo_url=item.AirLineLogo,
            )
            for item in airline_items
        ]

        return AirlineListResponse(airlines=airline_list_items)


def get_flights_client(current_user: "UserPublic | None") -> FlightLogicClient:
    """Get FlightLogic client with environment-aware configuration."""
    # Determine environment based on multiple factors
    if (
        settings.ENVIRONMENT in ["development", "staging"]
        or getattr(current_user, "is_tester", False)
        or (
            current_user
            and any(user["email"] == current_user.email for user in TEST_USERS)
        )
    ):
        environment = FlightAPIEnvironment.TEST
    else:
        environment = FlightAPIEnvironment.PRODUCTION
        user_email = current_user.email if current_user else "anonymous"
        logger.info(f"PRODUCTION mode - User: {user_email}")

    return FlightLogicClient(environment)
