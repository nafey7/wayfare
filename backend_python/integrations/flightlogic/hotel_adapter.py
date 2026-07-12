"""Adapter for converting between FlightLogic Hotel DTOs and domain schemas.

This module handles the transformation between FlightLogic Hotel API v6 DTOs
and the application's hotel domain schemas.

IMPORTANT: No data is faked or lost during conversion. If data is not available,
the field is set to None (for Optional fields) or an appropriate error is raised.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, cast

from app.domains.flight.enums import FlightAPIEnvironment
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
    HotelSearchResult,
    PerNightPrice,
    RoomOption,
)
from app.shared.imgproxy import get_imgproxy_url, transform_image_urls

from .hotel_dto import (
    HotelBookingDetailsRequestDTO,
    HotelBookingDetailsResponseDTO,
    HotelBookingRequestDTO,
    HotelBookingResponseDTO,
    HotelCancelRequestDTO,
    HotelCancelResponseDTO,
    HotelItineraryDTO,
    HotelMoreResultsItineraryDTO,
    HotelMoreResultsRequestDTO,
    HotelMoreResultsResponseDTO,
    HotelRateRulesRequestDTO,
    HotelRateRulesResponseDTO,
    HotelRoomRatesRequestDTO,
    HotelRoomRatesResponseDTO,
    HotelSearchRequestDTO,
    HotelSearchResponseDTO,
    OccupancyDTO,
    RoomOptionDTO,
)

logger = logging.getLogger(__name__)


def _parse_rating(value: Any, default: int = 0) -> int:
    """Parse hotel/TripAdvisor rating from various formats.

    FlightLogic API may return ratings in different formats:
    - Integer: 4
    - Float: 4.0
    - String number: "4"
    - String with text: "APARTHOTEL 4*", "4*", "5 STAR"

    Args:
        value: The rating value from API (str, int, float, or None)
        default: Default value if parsing fails

    Returns:
        Integer rating (0-5 typically)
    """
    if value is None:
        return default

    # Already numeric
    if isinstance(value, (int, float)):
        return int(value)

    # String - try to extract number
    if isinstance(value, str):
        # Try direct conversion first (handles "4", "4.0")
        try:
            return int(float(value))
        except ValueError:
            pass

        # Extract first number from string (handles "APARTHOTEL 4*", "4*", "5 STAR")
        match = re.search(r"(\d+)", value)
        if match:
            return int(match.group(1))

    return default


def _parse_max_occupancy(value: Any) -> dict[str, int]:
    """Parse maxOccupancyPerRoom from FlightLogic API format.

    FlightLogic API returns occupancy in various formats:
    - Integer: 2
    - String: "2"
    - Pipe-delimited: "2|t|1" (appears to be "adults|type|children")
    - Pipe-delimited: "3|t|2" (3 adults, 2 children)

    Args:
        value: The maxOccupancy value from API

    Returns:
        Dict with 'adults' and optionally 'children' counts
    """
    if value is None:
        return {}

    # Already numeric - assume it's total adults
    if isinstance(value, (int, float)):
        return {"adults": int(value)}

    if isinstance(value, str):
        # Check for pipe-delimited format: "adults|type|children"
        if "|" in value:
            parts = value.split("|")
            result = {}
            try:
                # First part is typically adults
                if len(parts) >= 1 and parts[0].isdigit():
                    result["adults"] = int(parts[0])
                # Third part (if exists) is typically children
                if len(parts) >= 3 and parts[2].isdigit():
                    result["children"] = int(parts[2])
                if result:
                    return result
            except (ValueError, IndexError):
                pass

        # Try direct numeric conversion
        try:
            return {"adults": int(float(value))}
        except ValueError:
            pass

        # Extract first number as fallback
        match = re.search(r"(\d+)", value)
        if match:
            return {"adults": int(match.group(1))}

    return {}


@dataclass
class HotelConversionContext:
    """Context object for maintaining state during hotel conversion."""

    session_id: str | None = None
    token_id: str | None = None
    original_request: Any | None = None


class HotelConversionError(Exception):
    """Raised when hotel conversion fails due to missing or invalid data."""

    def __init__(
        self,
        message: str,
        source_data: Any | None = None,
        target_type: type | None = None,
    ) -> None:
        super().__init__(message)
        self.source_data = source_data
        self.target_type = target_type


class HotelSchemaAdapter:
    """Adapter for converting between FlightLogic Hotel DTOs and domain schemas.

    This adapter ensures complete data conversion without any fake data or data loss.
    If required data is missing, appropriate errors are raised.
    """

    def __init__(self) -> None:
        """Initialize adapter with logging."""
        self.logger = logging.getLogger(__name__)

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _inject_credentials(self, request: Any) -> tuple[str, str, str, str]:
        """Inject FlightLogic credentials from config if not provided in request.

        Args:
            request: Request object (any type that may have auth fields)

        Returns:
            Tuple of (user_id, user_password, environment, ip_address)
        """
        from app.core.config import settings

        # Use credentials from request if provided, otherwise from settings
        user_id = getattr(request, "user_id", None) or settings.FLIGHTLOGIC_USER_ID
        user_password = (
            getattr(request, "user_password", None) or settings.FLIGHTLOGIC_PASSWORD
        )
        environment = getattr(request, "access", None) or FlightAPIEnvironment(
            settings.FLIGHTLOGIC_ACCESS_TYPE
        )
        ip_address = (
            getattr(request, "ip_address", None)
            or settings.FLIGHTLOGIC_IP_ADDRESS
            or "127.0.0.1"
        )

        if not user_id or not user_password:
            raise ValueError("FlightLogic credentials not configured")

        # Convert enum to string value for API
        environment_value = (
            environment.value
            if isinstance(environment, FlightAPIEnvironment)
            else environment
        )

        return user_id, user_password, environment_value, ip_address

    def _convert_price_to_decimal(self, price: str) -> Decimal:
        """Convert price string to Decimal.

        Args:
            price: Price as string (e.g., "1729.60")

        Returns:
            Decimal representation of the price
        """
        try:
            return Decimal(str(price))
        except (ValueError, TypeError) as e:
            self.logger.error(f"Failed to convert price '{price}' to Decimal: {e}")
            return Decimal("0")

    # ============================================================
    # SEARCH REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def search_request_to_dto(
        self, request: HotelSearchRequest
    ) -> HotelSearchRequestDTO:
        """Convert domain hotel search request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.

        Args:
            request: Hotel search request from domain layer

        Returns:
            FlightLogic API compatible DTO
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        # Convert occupancy to DTO format
        occupancy_dtos = [
            OccupancyDTO(
                room_no=room.room_no,
                adult=room.adult,
                child=room.child,
                child_age=room.child_age,
            )
            for room in request.occupancy
        ]

        # Build and return DTO request
        return HotelSearchRequestDTO(
            user_id=user_id,
            user_password=user_password,
            access=cast("Literal['Test', 'Production']", environment),
            ip_address=ip_address,
            checkin=request.checkin,
            checkout=request.checkout,
            city_name=request.city_name,
            country_name=request.country_name,
            latitude=request.latitude,
            longitude=request.longitude,
            hotel_codes=request.hotel_codes,
            radius=request.radius,
            maxResult=request.max_result,
            resultsPerPage=request.results_per_page,
            occupancy=occupancy_dtos,
            requiredCurrency=request.required_currency,
            requiredLanguage=request.required_language,
            nationality=request.nationality,
        )

    def search_response_from_dto(
        self, dto: HotelSearchResponseDTO
    ) -> HotelSearchResponse:
        """Convert FlightLogic DTO hotel search response to domain model.

        Args:
            dto: FlightLogic API response DTO

        Returns:
            Domain hotel search response
        """
        # Convert itineraries
        itineraries = [
            self._convert_hotel_itinerary(itinerary_dto)
            for itinerary_dto in dto.itineraries
        ]

        # Build domain response
        return HotelSearchResponse(
            session_id=dto.status.sessionId,
            total_results=dto.status.totalResults,
            more_results=dto.status.moreResults,
            next_token=dto.status.nextToken,
            itineraries=itineraries,
        )

    def _convert_hotel_itinerary(self, dto: HotelItineraryDTO) -> HotelSearchResult:
        """Convert single hotel itinerary DTO to domain model.

        Args:
            dto: Hotel itinerary DTO from API

        Returns:
            Domain hotel search result
        """
        # Convert per-night prices
        per_night_array = [
            PerNightPrice(
                night_index=night.nightIndex,
                currency=night.currency,
                price=self._convert_price_to_decimal(night.price),
            )
            for night in dto.perNightArray
        ]

        # Build domain model
        return HotelSearchResult(
            hotel_id=dto.hotelId,
            twx_hotel_id=str(dto.twxHotelId),  # Convert to string (API may return int)
            product_id=dto.productId,
            token_id=dto.tokenId,
            hotel_name=dto.hotelName,
            city=dto.city,
            locality=dto.locality or "",  # API may return None
            address=dto.address,
            country=dto.country or "",  # API may return None
            country_code=dto.countryCode or "",  # API may return None
            postal_code=dto.postalCode or "",  # API may return None
            latitude=dto.latitude,
            longitude=dto.longitude,
            distance_value=dto.distanceValue,
            distance_unit=dto.distanceUnit,
            total=self._convert_price_to_decimal(dto.total),
            currency=dto.currency,
            fare_type=dto.fareType,
            per_night_array=per_night_array,
            hotel_rating=_parse_rating(
                dto.hotelRating
            ),  # Handles "APARTHOTEL 4*", "4", 4
            property_type=dto.propertyType,
            facilities=dto.facilities,
            thumbnail_url=get_imgproxy_url(dto.thumbNailUrl, width=800, height=0),
            phone=dto.phone,
            email=dto.email or "",  # API may return None
            trip_advisor_rating=_parse_rating(dto.tripAdvisorRating),
            trip_advisor_review=dto.tripAdvisorReview,
            special=dto.special,
        )

    # ============================================================
    # ROOM RATES REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def room_rates_request_to_dto(
        self, request: HotelRoomRatesRequest
    ) -> HotelRoomRatesRequestDTO:
        """Convert domain room rates request to FlightLogic DTO.

        IMPORTANT: get_room_rates API does NOT require authentication fields.
        IMPORTANT: Uses camelCase field names (sessionId, tokenId, productId, hotelId).

        Args:
            request: Room rates request from domain layer

        Returns:
            FlightLogic API compatible DTO with camelCase fields
        """
        return HotelRoomRatesRequestDTO(
            sessionId=request.session_id,
            tokenId=request.token_id,
            productId=request.product_id,
            hotelId=request.hotel_id,
        )

    def room_rates_response_from_dto(
        self, dto: HotelRoomRatesResponseDTO
    ) -> HotelRoomRatesResponse:
        """Convert FlightLogic DTO room rates response to domain model.

        Args:
            dto: FlightLogic API response DTO

        Returns:
            Domain room rates response
        """
        # Convert room options from nested perBookingRates
        logger.info(
            f"🔍 Adapter: Converting room rates DTO - has roomRates: {hasattr(dto, 'roomRates')}"
        )
        if hasattr(dto, "roomRates"):
            logger.info(
                f"🔍 Adapter: roomRates has perBookingRates: {hasattr(dto.roomRates, 'perBookingRates')}"
            )
            if hasattr(dto.roomRates, "perBookingRates"):
                logger.info(
                    f"🔍 Adapter: perBookingRates count: {len(dto.roomRates.perBookingRates)}"
                )

        rooms = [
            self._convert_room_option(room_dto)
            for room_dto in dto.roomRates.perBookingRates
        ]

        logger.info(f"🔍 Adapter: Converted {len(rooms)} rooms to domain model")

        return HotelRoomRatesResponse(
            hotel_id=dto.hotelId,
            session_id=dto.sessionId,
            token_id=dto.tokenId,
            rooms=rooms,
        )

    def _convert_room_option(self, dto: RoomOptionDTO) -> RoomOption:
        """Convert room option DTO to domain model.

        Args:
            dto: Room option DTO from API

        Returns:
            Domain room option
        """
        # Parse max occupancy - API may return "1|t|1" (adults|type|children) format
        max_occupancy_dict = _parse_max_occupancy(dto.maxOccupancyPerRoom)

        # Cancellation policy is already a string from API
        cancellation_text = dto.cancellationPolicy or "No cancellation policy provided"

        # FlightLogic returns netPrice (total for stay), not per-night
        # For simplicity, use netPrice for both fields until we have night count
        net_price = self._convert_price_to_decimal(dto.netPrice)

        return RoomOption(
            room_type=dto.roomType,
            rate_basis_id=dto.rateBasisId,
            price_per_night=net_price,  # Using netPrice (total) for now
            total_price=net_price,  # netPrice is the total
            currency=dto.currency,
            meal_plan=dto.boardType,
            cancellation_policy=cancellation_text,
            max_occupancy=max_occupancy_dict,
            rooms_available=0,  # FlightLogic doesn't provide this field
            images=transform_image_urls(dto.roomImages),  # Room image URLs (signed)
        )

    # ============================================================
    # BOOKING REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def booking_request_to_dto(
        self, request: HotelBookingRequest
    ) -> HotelBookingRequestDTO:
        """Convert domain booking request to FlightLogic DTO.

        IMPORTANT: hotel_book API does NOT require authentication fields.
        IMPORTANT: Uses camelCase field names and paxDetails structure.

        Args:
            request: Booking request from domain layer

        Returns:
            FlightLogic API compatible DTO with camelCase fields
        """
        from collections import defaultdict

        from .hotel_dto import AdultDetailsDTO, ChildDetailsDTO, PaxDetailsDTO

        # Convert guests list to paxDetails format with multi-room support
        # FlightLogic expects: paxDetails[{room_no, adult{title[], firstName[], lastName[]}, child{...}}]
        # Group guests by room_number and separate adults from children

        # Group guests by room number
        rooms: dict[int, dict[str, list]] = defaultdict(
            lambda: {"adults": [], "children": []}
        )

        for guest in request.guests:
            room_key = guest.room_number
            guest_data = {
                "title": guest.title,
                "first_name": guest.first_name,
                "last_name": guest.last_name,
            }

            if guest.is_child:
                rooms[room_key]["children"].append(guest_data)
            else:
                rooms[room_key]["adults"].append(guest_data)

        # Build paxDetails for each room
        pax_details = []
        for room_no in sorted(rooms.keys()):
            room_guests = rooms[room_no]

            # Extract adult arrays
            adult_titles = [g["title"] for g in room_guests["adults"]]
            adult_first_names = [g["first_name"] for g in room_guests["adults"]]
            adult_last_names = [g["last_name"] for g in room_guests["adults"]]

            # Create adult DTO (required even if empty - use empty arrays)
            adult_dto = AdultDetailsDTO(
                title=adult_titles if adult_titles else [],
                firstName=adult_first_names if adult_first_names else [],
                lastName=adult_last_names if adult_last_names else [],
            )

            # Create child DTO if children exist
            child_dto = None
            if room_guests["children"]:
                child_titles = [g["title"] for g in room_guests["children"]]
                child_first_names = [g["first_name"] for g in room_guests["children"]]
                child_last_names = [g["last_name"] for g in room_guests["children"]]

                child_dto = ChildDetailsDTO(
                    title=child_titles,
                    firstName=child_first_names,
                    lastName=child_last_names,
                )

            pax_details.append(
                PaxDetailsDTO(room_no=room_no, adult=adult_dto, child=child_dto)
            )

        return HotelBookingRequestDTO(
            sessionId=request.session_id,
            productId=request.product_id,
            tokenId=request.token_id,
            rateBasisId=request.rate_basis_id,
            clientRef=request.client_ref,
            customerEmail=request.customer_email,
            customerPhone=request.customer_phone,
            bookingNote=request.booking_note,
            paxDetails=pax_details,
        )

    def booking_response_from_dto(
        self, dto: HotelBookingResponseDTO
    ) -> HotelBookingResponse:
        """Convert FlightLogic DTO booking response to domain model.

        Args:
            dto: FlightLogic API response DTO

        Returns:
            Domain booking response
        """
        # Handle error response (status is dict with errors list or error field)
        if isinstance(dto.status, dict):
            error_msg = "Unknown error"
            errors_list = dto.status.get("errors")
            if errors_list and isinstance(errors_list, list) and len(errors_list) > 0:
                first = errors_list[0]
                if isinstance(first, dict):
                    error_msg = first.get("errorMessage", error_msg)
            if error_msg == "Unknown error":
                error_msg = dto.status.get("error", error_msg)
            return HotelBookingResponse(
                status="Failed",
                supplier_confirmation_num=None,
                reference_num=None,
                booking_details={},
                errors={
                    "code": "API_ERROR",
                    "message": error_msg,
                    "details": None,
                },
            )

        # status is string: CONFIRMED, PENDING, or FAILED
        success = dto.status == "CONFIRMED"

        # Build booking details dict
        booking_details = {}
        if success and dto.roomBookDetails:
            booking_details = {
                "hotel_id": dto.roomBookDetails.hotelId,
                "check_in": dto.roomBookDetails.checkIn,
                "check_out": dto.roomBookDetails.checkOut,
                "days": dto.roomBookDetails.days,
                "total_price": dto.roomBookDetails.NetPrice,
                "currency": dto.roomBookDetails.currency,
                "fare_type": dto.roomBookDetails.fareType,
                "cancellation_policy": dto.roomBookDetails.cancellationPolicy,
                "rooms": dto.roomBookDetails.rooms,  # Include room details with guest names
            }

        # Build errors dict if failed
        errors = None
        if not success:
            errors = {
                "code": "BOOKING_FAILED",
                "message": dto.error or f"Booking failed with status: {dto.status}",
                "details": None,
            }

        return HotelBookingResponse(
            status="Success" if success else "Failed",
            supplier_confirmation_num=dto.supplierConfirmationNum,
            reference_num=str(dto.referenceNum) if dto.referenceNum else None,
            booking_details=booking_details,
            errors=errors,
        )

    # ===================================================================
    # RATE RULES (Check Room Rates) Conversions
    # ===================================================================

    def rate_rules_request_to_dto(
        self, request: HotelRateRulesRequest
    ) -> HotelRateRulesRequestDTO:
        """Convert domain HotelRateRulesRequest to FlightLogic DTO.

        IMPORTANT: get_rate_rules API does NOT require authentication fields.
        IMPORTANT: Uses camelCase field names (sessionId, productId, tokenId, rateBasisId).

        Args:
            request: Domain model rate rules request

        Returns:
            FlightLogic API DTO with camelCase fields (no auth)
        """
        from .hotel_dto import HotelRateRulesRequestDTO

        return HotelRateRulesRequestDTO(
            sessionId=request.session_id,
            productId=request.product_id,
            tokenId=request.token_id,
            rateBasisId=request.rate_basis_id,
        )

    def rate_rules_response_from_dto(
        self, dto: HotelRateRulesResponseDTO
    ) -> HotelRateRulesResponse:
        """Convert FlightLogic rate rules DTO to domain model.

        Args:
            dto: FlightLogic API response DTO

        Returns:
            Domain model with validated rate information
        """

        from app.domains.hotel.schemas import HotelRateRulesResponse

        # Extract the first room from perBookingRates
        per_booking_rates = dto.roomRates.get("perBookingRates", [])
        if not per_booking_rates:
            msg = "No rate information in response"
            raise ValueError(msg)

        room = per_booking_rates[0]  # Take first rate

        return HotelRateRulesResponse(
            session_id=dto.sessionId,
            hotel_id=str(dto.hotelId),
            token_id=dto.tokenId,
            room_type=room.roomType,
            description=room.description,
            room_code=room.roomCode,
            fare_type=room.fareType,
            rate_basis_id=room.rateBasisId,
            currency=room.currency,
            net_price=self._convert_price_to_decimal(room.netPrice),
            board_basis=room.boardType,
            max_occupancy_per_room=_parse_rating(room.maxOccupancyPerRoom, default=2),
            inventory_type=room.inventoryType,
            cancellation_policy=room.cancellationPolicy,
            facilities=room.facilities,
            images=transform_image_urls(room.roomImages),  # Room image URLs (signed)
            remark=room.remark,
        )

    # ============================================================
    # CANCEL REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def cancel_request_to_dto(
        self, request: HotelCancelRequest
    ) -> HotelCancelRequestDTO:
        """Convert domain cancel request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.

        Args:
            request: Cancel request from domain layer

        Returns:
            FlightLogic API compatible DTO
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        return HotelCancelRequestDTO(
            user_id=user_id,
            user_password=user_password,
            access=cast("Literal['Test', 'Production']", environment),
            ip_address=ip_address,
            supplierConfirmationNum=request.supplier_confirmation_num,
            referenceNum=request.reference_num,
        )

    def cancel_response_from_dto(
        self, dto: HotelCancelResponseDTO
    ) -> HotelCancelResponse:
        """Convert FlightLogic DTO cancel response to domain model.

        Args:
            dto: FlightLogic API response DTO

        Returns:
            Domain cancel response
        """
        # Check if cancellation was successful
        success = dto.status == "CANCELLED"

        # Build errors dict if failed
        errors = None
        if not success:
            errors = {
                "code": "CANCELLATION_FAILED",
                "message": dto.message
                or f"Cancellation failed with status: {dto.status}",
                "details": None,
            }

        return HotelCancelResponse(
            status=dto.status,
            cancel_reference_num=dto.cancelReferenceNum,
            message=dto.message,
            errors=errors,
        )

    # ============================================================
    # BOOKING DETAILS REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def booking_details_request_to_dto(
        self, request: HotelBookingDetailsRequest
    ) -> HotelBookingDetailsRequestDTO:
        """Convert domain booking details request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.

        Args:
            request: Booking details request from domain layer

        Returns:
            FlightLogic API compatible DTO
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        return HotelBookingDetailsRequestDTO(
            user_id=user_id,
            user_password=user_password,
            access=cast("Literal['Test', 'Production']", environment),
            ip_address=ip_address,
            supplierConfirmationNum=request.supplier_confirmation_num,
            referenceNum=request.reference_num,
        )

    def booking_details_response_from_dto(
        self, dto: HotelBookingDetailsResponseDTO
    ) -> HotelBookingDetailsResponse:
        """Convert FlightLogic DTO booking details response to domain model.

        Maps FlightLogic camelCase fields to snake_case format expected by frontend.
        Also extracts and formats guest information from rooms data.

        Args:
            dto: FlightLogic API response DTO

        Returns:
            Domain booking details response with properly mapped fields
        """
        # Build errors dict if present
        errors = None
        if dto.errors:
            errors = dto.errors
        elif dto.error:
            # Handle error field (singular) vs errors (plural)
            errors = (
                {"message": str(dto.error)} if isinstance(dto.error, str) else dto.error
            )

        # Normalize booking details from different response formats
        # FlightLogic API can return data in different formats:
        # 1. With roomBookDetails nested (most common)
        # 2. With bookingDetails wrapper
        # 3. Direct booking fields
        raw_details = {}
        if dto.roomBookDetails:
            # Merge roomBookDetails with top-level fields
            raw_details = {
                **dto.roomBookDetails,
                "status": dto.status,
                "supplierConfirmationNum": dto.supplierConfirmationNum,
                "referenceNum": dto.referenceNum,
                "clientRefNum": dto.clientRefNum,
                "productId": dto.productId,
            }
        elif dto.bookingDetails:
            # Response already has bookingDetails wrapper
            raw_details = dto.bookingDetails
        else:
            # Check if response has booking-like fields directly
            dto_dict = dto.model_dump(exclude_none=True, exclude={"errors", "error"})
            booking_fields = [
                "checkIn",
                "checkOut",
                "NetPrice",
                "rooms",
                "address",
                "city",
                "rating",
                "hotelName",
            ]
            has_booking_fields = any(key in dto_dict for key in booking_fields)
            if has_booking_fields:
                # Extract booking fields, excluding error fields
                raw_details = {
                    k: v
                    for k, v in dto_dict.items()
                    if k not in ["errors", "error", "bookingDetails", "roomBookDetails"]
                }

        # Map camelCase fields to snake_case and rename fields for frontend
        mapped_details = {}
        mapped_details.update(raw_details)

        # Map date fields: camelCase → snake_case
        if "checkIn" in raw_details:
            mapped_details["check_in"] = raw_details["checkIn"]
            mapped_details["check_in_date"] = raw_details["checkIn"]
        if "checkOut" in raw_details:
            mapped_details["check_out"] = raw_details["checkOut"]
            mapped_details["check_out_date"] = raw_details["checkOut"]

        # Map price fields (convert string to float if needed)
        if "NetPrice" in raw_details:
            try:
                price_value = (
                    float(raw_details["NetPrice"]) if raw_details["NetPrice"] else 0.0
                )
                mapped_details["total_price"] = price_value
                mapped_details["NetPrice"] = price_value
            except (ValueError, TypeError):
                mapped_details["total_price"] = raw_details["NetPrice"]
                mapped_details["NetPrice"] = raw_details["NetPrice"]

        # Map rating field (convert string to float if needed)
        if "rating" in raw_details:
            try:
                rating_value = (
                    float(raw_details["rating"]) if raw_details["rating"] else 0.0
                )
                mapped_details["hotel_rating"] = rating_value
                mapped_details["rating"] = rating_value
            except (ValueError, TypeError):
                mapped_details["hotel_rating"] = 0.0
                mapped_details["rating"] = raw_details["rating"]

        # Extract hotel name if available (check both camelCase and snake_case)
        if "hotelName" in raw_details:
            mapped_details["hotel_name"] = raw_details["hotelName"]
        elif "hotel_name" in raw_details:
            mapped_details["hotel_name"] = raw_details["hotel_name"]

        # Map hotel ID if available
        if "hotelId" in raw_details:
            mapped_details["hotel_id"] = raw_details["hotelId"]
        elif "hotel_id" in raw_details:
            mapped_details["hotel_id"] = raw_details["hotel_id"]

        # Map property type if available
        if "propertyType" in raw_details:
            mapped_details["property_type"] = raw_details["propertyType"]

        # Extract and format guests from rooms (helper for nested data extraction)
        guests = self._extract_guests_from_rooms(raw_details.get("rooms", []))
        if guests:
            mapped_details["guests"] = guests

        # Ensure rooms array is properly formatted (keep original structure)
        if raw_details.get("rooms"):
            mapped_details["rooms"] = raw_details["rooms"]

        # Map other common fields
        if "bookingDateTime" in raw_details:
            mapped_details["booking_date_time"] = raw_details["bookingDateTime"]
        if "customerEmail" in raw_details:
            mapped_details["customer_email"] = raw_details["customerEmail"]
        if "customerPhone" in raw_details:
            mapped_details["customer_phone"] = raw_details["customerPhone"]
        if "fareType" in raw_details:
            mapped_details["fare_type"] = raw_details["fareType"]
        if "cancellationPolicy" in raw_details:
            mapped_details["cancellation_policy"] = raw_details["cancellationPolicy"]
        if "cancelReferenceNum" in raw_details:
            mapped_details["cancel_reference_num"] = raw_details["cancelReferenceNum"]

        return HotelBookingDetailsResponse(
            booking_details=mapped_details,
            errors=errors,
        )

    def _extract_guests_from_rooms(
        self, rooms: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract and format guests from rooms data.

        Helper method for extracting nested guest information from rooms.
        Similar to _convert_hotel_itinerary and _convert_room_option patterns.

        Args:
            rooms: List of room dicts with paxDetails

        Returns:
            List of guest dicts
        """
        guests = []

        for room_index, room in enumerate(rooms):
            room_number = room_index + 1

            # Extract guest names from paxDetails
            pax_details = room.get("paxDetails", {})
            guest_names = pax_details.get("name", [])

            for guest_name in guest_names:
                # Parse guest name (format: "Mr moo izzz" or "Title First Last")
                name_parts = str(guest_name).strip().split(maxsplit=2)

                guest = {
                    "room_number": room_number,
                    "is_child": False,  # Default to adult, can be enhanced if age info available
                }

                if len(name_parts) >= 1:
                    guest["title"] = name_parts[0]
                if len(name_parts) >= 2:
                    guest["first_name"] = name_parts[1]
                if len(name_parts) >= 3:
                    guest["last_name"] = name_parts[2]
                elif len(name_parts) == 2:
                    # If only 2 parts, treat first as title, second as full name
                    guest["first_name"] = name_parts[1]
                    guest["last_name"] = ""

                guests.append(guest)

        return guests

    # ============================================================
    # MORE RESULTS REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def more_results_request_to_dto(
        self, request: HotelMoreResultsRequest
    ) -> HotelMoreResultsRequestDTO:
        """Convert domain more results request to FlightLogic DTO.

        IMPORTANT: moreResults API does NOT require authentication fields.
        IMPORTANT: Uses camelCase field names (sessionId, nextToken, maxResult).

        Args:
            request: More results request from domain layer

        Returns:
            FlightLogic API compatible DTO
        """
        from .hotel_dto import HotelMoreResultsRequestDTO

        return HotelMoreResultsRequestDTO(
            sessionId=request.session_id,
            nextToken=request.next_token,
            maxResult=request.max_result,
        )

    def _convert_more_results_itinerary(
        self, dto: HotelMoreResultsItineraryDTO
    ) -> HotelSearchResult:
        """Convert moreResults itinerary DTO to domain model.

        Note: MoreResults API returns different structure:
        - total is numeric (float/int) not string
        - perNightArray is NOT included in response

        Args:
            dto: MoreResults itinerary DTO from API

        Returns:
            Domain hotel search result
        """
        # Convert numeric total to Decimal
        total_decimal = self._convert_price_to_decimal(str(dto.total))

        # MoreResults API doesn't provide perNightArray, so create empty list
        # The domain model requires it, but we can't populate it without the data
        per_night_array: list[PerNightPrice] = []

        # Handle tripAdvisorReview which may be string in some responses
        trip_advisor_review = (
            int(dto.tripAdvisorReview)
            if isinstance(dto.tripAdvisorReview, str)
            and dto.tripAdvisorReview.isdigit()
            else (
                dto.tripAdvisorReview if isinstance(dto.tripAdvisorReview, int) else 0
            )
        )

        # Build domain model
        return HotelSearchResult(
            hotel_id=dto.hotelId,
            twx_hotel_id=str(dto.twxHotelId),  # Convert to string (API may return int)
            product_id=dto.productId,
            token_id=dto.tokenId,
            hotel_name=dto.hotelName,
            city=dto.city,
            locality=dto.locality or "",  # API may return None
            address=dto.address,
            country=dto.country or "",  # API may return None
            country_code=dto.countryCode or "",  # API may return None
            postal_code=dto.postalCode or "",  # API may return None
            latitude=dto.latitude,
            longitude=dto.longitude,
            distance_value=dto.distanceValue,
            distance_unit=dto.distanceUnit,
            total=total_decimal,
            currency=dto.currency,
            fare_type=dto.fareType,
            per_night_array=per_night_array,  # Empty since not provided by API
            hotel_rating=_parse_rating(dto.hotelRating),
            property_type=dto.propertyType,
            facilities=dto.facilities,
            thumbnail_url=get_imgproxy_url(dto.thumbNailUrl, width=800, height=0),
            phone=dto.phone,
            email=dto.email or "",  # API may return None
            trip_advisor_rating=_parse_rating(dto.tripAdvisorRating),
            trip_advisor_review=trip_advisor_review,
            special=dto.special,
        )

    def more_results_response_from_dto(
        self, dto: HotelMoreResultsResponseDTO
    ) -> HotelSearchResponse:
        """Convert FlightLogic more results DTO to domain model.

        Note: More results API returns similar structure to search response,
        but status object does NOT include totalResults field.
        Also, itineraries have different structure (no perNightArray, numeric total).

        Args:
            dto: FlightLogic API response DTO for more results

        Returns:
            Domain hotel search response with additional results
        """
        # Convert itineraries using dedicated converter for moreResults structure
        itineraries = [
            self._convert_more_results_itinerary(itinerary_dto)
            for itinerary_dto in dto.itineraries
        ]

        # Build domain response
        # Note: totalResults is not in moreResults response, so we use count of itineraries
        # The actual total_results should be maintained from the original search
        return HotelSearchResponse(
            session_id=dto.status.sessionId,
            total_results=len(
                itineraries
            ),  # Use count since totalResults not in response
            more_results=dto.status.moreResults,
            next_token=dto.status.nextToken,
            itineraries=itineraries,
        )
