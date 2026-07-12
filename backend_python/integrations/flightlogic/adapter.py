"""Adapter for converting between FlightLogic DTOs and domain schemas.

This module handles the transformation between FlightLogic API DTOs
and the application's domain schemas without modifying existing code.

IMPORTANT: No data is faked or lost during conversion. If data is not available,
the field is set to None (for Optional fields) or an appropriate error is raised.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any

from app.domains.common.schemas import (
    DateTime,
    Duration,
    ErrorDetails,
    MoneyAmount,
)
from app.domains.flight.enums import (
    BaggageUnit,
    BookingStatus,
    CabinClass,
    CabinClassText,
    CheckInLocation,
    FareRuleCategory,
    FareType,
    FlightAPIEnvironment,
    JourneyType,
    MarriageGroup,
    MealCode,
    PassengerType,
    PNRStatus,
    RequiredBookingField,
    ServiceBehavior,
    TicketStatus,
    TicketType,
)
from app.domains.flight.schemas import (
    AircraftInfo,
    AirlineInfo,
    AirlinePNR,
    AirportInfo,
    AvailableExtraServices,
    BaggageAllowance,
    BaggageAllowanceInfo,
    BaggageInformation,
    BaggageServiceCategory,
    BaggageServiceOption,
    BookingClassCode,
    BookingNote,
    CabinBaggageAllowance,
    ContactInformation,
    ExtraService,
    ExtraServicesData,
    FareBasisCode,
    FareBreakdown,
    FareItinerary,
    FarePricing,
    FareRuleDetails,
    FareTotals,
    FlightBookingRequest,
    FlightBookingResponse,
    FlightCancelRequest,
    FlightCancelResponse,
    FlightExtraServicesRequest,
    FlightExtraServicesResponse,
    FlightFareRulesRequest,
    FlightFareRulesResponse,
    FlightLeg,
    FlightNumber,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    FlightSegment,
    InboundFareData,
    IndividualPassengerFare,
    MealServiceCategory,
    MealServiceOption,
    PassengerDetails,
    PassengerFareBreakdown,
    PassengerTypeInfo,
    PenaltyDetails,
    PersonalInfo,
    PersonName,
    PostalCode,
    RouteCode,
    SeatAvailability,
    SeatServiceCategory,
    ServiceDescription,
    StopDetail,
    TaxDetails,
    TerminalInfo,
    TicketOrderRequest,
    TicketOrderResponse,
    TravelDocuments,
    TripDetailsFlightSegment,
    TripDetailsRequest,
    TripDetailsResponse,
    UpdatedFarePricing,
    ValidatedFareItinerary,
    ValidatedFareTotals,
)

from .dto import (
    AdultPassenger as DtoAdultPassenger,
)
from .dto import (
    AmountInfo,
    DynamicService,
    FlightBookingInfo,
    FlightLogicBookingRequest,
    FlightLogicBookingResponse,
    FlightLogicCancelRequest,
    FlightLogicCancelResponse,
    FlightLogicError,
    FlightLogicExtraServicesRequest,
    FlightLogicExtraServicesResponse,
    FlightLogicFareRulesRequest,
    FlightLogicFareRulesResponse,
    FlightLogicRevalidateRequest,
    FlightLogicRevalidateResponse,
    FlightLogicSearchRequest,
    FlightLogicSearchResponse,
    FlightLogicTicketRequest,
    FlightLogicTicketResponse,
    FlightLogicTripDetailsRequest,
    FlightLogicTripDetailsResponse,
    OriginDestinationInfo,
    PaxDetails,
    PaxInfo,
    TripDetailsBooking,
)
from .dto import (
    BaggageInfo as DtoBaggageInfo,
)
from .dto import (
    ChildPassenger as DtoChildPassenger,
)
from .dto import (
    FareRule as DtoFareRule,
)
from .dto import (
    FlightSegment as DtoFlightSegment,
)
from .dto import (
    InfantPassenger as DtoInfantPassenger,
)
from .ticket_status_parsing import parse_ticket_status_from_flightlogic_string

logger = logging.getLogger(__name__)


def _parse_datetime_string(datetime_string: str) -> datetime:
    """Parse FlightLogic datetime string to datetime object.

    FlightLogic uses various datetime formats. This function handles the common ones.
    """
    if not datetime_string:
        raise ValueError("Empty datetime string")

    # Common FlightLogic formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",  # 2024-12-25T15:30:00
        "%Y-%m-%d %H:%M:%S",  # 2024-12-25 15:30:00
        "%Y-%m-%dT%H:%M:%S.%f",  # With microseconds
        "%Y-%m-%d",  # Date only
    ]

    for fmt in formats:
        try:
            # Keep as naive datetime (local airport time) - no timezone conversion
            # DTZ007 suppressed as we intentionally keep naive datetime
            return datetime.strptime(datetime_string, fmt)  # noqa: DTZ007
        except ValueError:
            continue

    # If no format worked, try parsing with fromisoformat (Python 3.7+)
    try:
        dt = datetime.fromisoformat(datetime_string.replace("Z", "+00:00"))
        # Remove timezone info to keep as naive datetime (local airport time)
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    except ValueError:
        pass

    raise ValueError(f"Unable to parse datetime string: {datetime_string}")


@dataclass
class ConversionContext:
    """Context object for maintaining state during conversion."""

    session_id: str | None = None
    fare_source_code: str | None = None
    inbound_fare_source_code: str | None = None
    original_request: Any | None = None
    supplier: str | None = None


class ConversionError(Exception):
    """Raised when conversion fails due to missing or invalid data."""

    def __init__(
        self,
        message: str,
        source_data: Any | None = None,
        target_type: type | None = None,
    ) -> None:
        super().__init__(message)
        self.source_data = source_data
        self.target_type = target_type


class FlightLogicSchemaAdapter:
    """Adapter for converting between FlightLogic DTOs and domain schemas.

    This adapter ensures complete data conversion without any fake data or data loss.
    If required data is missing, appropriate errors are raised.
    """

    def __init__(self) -> None:
        """Initialize adapter with caching for common lookups."""
        self._airport_cache: dict[str, AirportInfo] = {}
        self._airline_cache: dict[str, AirlineInfo] = {}
        self._aircraft_cache: dict[str, AircraftInfo] = {}
        self.logger = logging.getLogger(__name__)

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def _inject_credentials(self, request) -> tuple[str, str, str, str]:
        """Inject FlightLogic credentials from config if not provided in request.

        Returns:
            Tuple of (user_id, user_password, environment, ip_address)
        """
        from app.core.config import settings

        # Use credentials from request if provided, otherwise from settings
        user_id = getattr(request, "user_id", None) or settings.FLIGHTLOGIC_USER_ID
        user_password = (
            getattr(request, "user_password", None) or settings.FLIGHTLOGIC_PASSWORD
        )
        environment = getattr(request, "environment", None) or FlightAPIEnvironment(
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

    # ============================================================
    # SEARCH REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def search_request_to_dto(
        self, request: FlightSearchRequest
    ) -> FlightLogicSearchRequest:
        """Convert domain search request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.

        For Return journeys, FlightLogic expects a single OriginDestinationInfo with:
        - departureDate: outbound departure date
        - returnDate: inbound departure date (from second segment)
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        origin_destination_info = []

        # For Return journey type, combine outbound and inbound into single segment
        if (
            request.journey_type == JourneyType.RETURN
            and len(request.origin_destination_info) >= 2
        ):
            outbound = request.origin_destination_info[0]
            inbound = request.origin_destination_info[1]

            dto_segment = OriginDestinationInfo(
                departureDate=outbound.departure_date.isoformat(),
                returnDate=inbound.departure_date.isoformat(),  # Return date from inbound segment
                airportOriginCode=outbound.origin_airport.iata_code,
                airportDestinationCode=outbound.destination_airport.iata_code,
            )
            origin_destination_info.append(dto_segment)
        else:
            # OneWay or Circle journey - use segments as-is
            for segment in request.origin_destination_info:
                dto_segment = OriginDestinationInfo(
                    departureDate=segment.departure_date.isoformat(),
                    returnDate=segment.return_date.isoformat()
                    if segment.return_date
                    else None,
                    airportOriginCode=segment.origin_airport.iata_code,
                    airportDestinationCode=segment.destination_airport.iata_code,
                )
                origin_destination_info.append(dto_segment)

        # Determine city-wise search flags, falling back to filters or DTO defaults.
        # The domain schema stores these flags both at top level (deprecated) and inside filters.
        # FlightLogic DTO requires strict booleans (no None), with True as the default.
        city_wise_search_origin = request.city_wise_search_origin
        city_wise_search_destination = request.city_wise_search_destination

        # If top-level flags are not provided, look at filters.
        if (
            city_wise_search_origin is None
            and request.filters is not None
            and request.filters.city_wise_search_origin is not None
        ):
            city_wise_search_origin = request.filters.city_wise_search_origin
        if (
            city_wise_search_destination is None
            and request.filters is not None
            and request.filters.city_wise_search_destination is not None
        ):
            city_wise_search_destination = request.filters.city_wise_search_destination

        # If still None, fall back to DTO defaults (True = search all airports in city).
        if city_wise_search_origin is None:
            city_wise_search_origin = True
        if city_wise_search_destination is None:
            city_wise_search_destination = True

        # Build the DTO with explicit children value
        # Note: Must use alias name "childs" because Field has alias="childs"
        return FlightLogicSearchRequest(
            user_id=user_id,
            user_password=user_password,
            access=environment,
            ip_address=ip_address,
            requiredCurrency=request.required_currency_code or "USD",
            journeyType=request.journey_type.value,
            OriginDestinationInfo=origin_destination_info,
            adults=request.adults,
            childs=request.children,  # Use alias name "childs" not "children"
            infants=request.infants,
            airlineCode=request.preferred_airline.iata_code
            if request.preferred_airline
            else None,
            directFlight=request.direct_flight,
            city_wise_search_origin=city_wise_search_origin,
            city_wise_search_destination=city_wise_search_destination,
            **{
                "class": request.cabin_class.value
            },  # cabin_class is always CabinClass enum
        )

    def search_response_from_dto(
        self, dto: FlightLogicSearchResponse, context: ConversionContext | None = None
    ) -> FlightSearchResponse:
        """Convert FlightLogic search response DTO to domain schema.

        Args:
            dto: FlightLogic search response DTO
            context: Optional conversion context with additional metadata

        Returns:
            Domain FlightSearchResponse

        Raises:
            ConversionError: If required data is missing
        """
        # Extract errors first (FlightLogic can return errors even with results)
        errors = None
        if dto.Errors:
            errors = [self._convert_error(dto.Errors, context)]

        # If there are errors and no AirSearchResponse, return early with errors
        if errors and not dto.AirSearchResponse:
            return FlightSearchResponse(
                session_id="",  # Required field
                supplier="",  # Required field
                fare_itineraries=[],  # Required field
                inbound_fare_itineraries=None,  # Required field for schema validation
                errors=errors,
            )

        if not dto.AirSearchResponse:
            raise ConversionError(
                "No AirSearchResponse in FlightLogic response",
                source_data=dto,
                target_type=FlightSearchResponse,
            )

        response_data = dto.AirSearchResponse

        # Process main search result (outbound or oneway)
        fare_itineraries = []
        if (
            response_data.AirSearchResult
            and response_data.AirSearchResult.FareItineraries
        ):
            fare_itineraries = self._process_fare_itineraries(
                response_data.AirSearchResult.FareItineraries
            )

        # Process inbound results for Indian domestic roundtrips
        inbound_fare_itineraries = None
        if (
            response_data.AirSearchResultInbound
            and response_data.AirSearchResultInbound.FareItineraries
        ):
            inbound_fare_itineraries = self._process_fare_itineraries(
                response_data.AirSearchResultInbound.FareItineraries
            )

        # Supplier defaults to FlightLogic since we're in the FlightLogic adapter
        supplier = response_data.supplier or "FlightLogic"

        return FlightSearchResponse(
            session_id=response_data.session_id,
            supplier=supplier,
            fare_itineraries=fare_itineraries,
            inbound_fare_itineraries=inbound_fare_itineraries,
            errors=errors,  # Include errors even when results exist
        )

    def _process_fare_itineraries(
        self, fare_itineraries_data: list[dict[str, Any]]
    ) -> list[FareItinerary]:
        """Process a list of fare dictionaries and convert to domain fare itineraries.

        Args:
            fare_itineraries_data: List of fare dictionary data from FlightLogic

        Returns:
            List of converted domain FareItinerary objects
        """
        result = []
        for fare_dict in fare_itineraries_data:
            itinerary_data = FlightLogicSchemaAdapter._extract_fare_itinerary_data(
                fare_dict
            )
            if itinerary_data:
                if isinstance(itinerary_data, list):
                    for item in itinerary_data:
                        result.append(self._convert_fare_itinerary(item))
                else:
                    result.append(self._convert_fare_itinerary(itinerary_data))
        return result

    @staticmethod
    def _extract_fare_itinerary_data(
        fare_dict: dict[str, Any],
    ) -> dict[str, Any] | list[dict[str, Any]] | None:
        """Safely extract fare itinerary data from dictionary.

        Returns:
            - A single fare itinerary dict
            - A list of fare itinerary dicts
            - None if no data found
        """
        if not isinstance(fare_dict, dict):
            return None

        fare_data = fare_dict.get("FareItinerary")

        # Validate the data is in expected format
        if fare_data is None:
            return None

        # If it's a list, ensure all items are dicts
        if isinstance(fare_data, list):
            if all(isinstance(item, dict) for item in fare_data):
                return fare_data
            raise ConversionError(
                "FareItinerary list contains non-dict items",
                source_data=fare_data,
                target_type=FareItinerary,
            )

        # If it's a single dict, return it
        if isinstance(fare_data, dict):
            return fare_data

        # Unexpected type
        raise ConversionError(
            f"FareItinerary has unexpected type: {type(fare_data).__name__}",
            source_data=fare_data,
            target_type=FareItinerary,
        )

    # ============================================================
    # REVALIDATION REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def revalidate_request_to_dto(
        self, request: FlightRevalidateRequest
    ) -> FlightLogicRevalidateRequest:
        """Convert domain revalidate request to FlightLogic DTO."""
        return FlightLogicRevalidateRequest(
            session_id=request.session_id,
            fare_source_code=request.fare_source_code,
            fare_source_code_inbound=request.return_fare_source_code,
        )

    def revalidate_response_from_dto(
        self,
        dto: FlightLogicRevalidateResponse,
        context: ConversionContext | None = None,
    ) -> FlightRevalidateResponse:
        """Convert FlightLogic revalidate response DTO to domain schema.

        Args:
            dto: FlightLogic revalidate response DTO
            context: Optional conversion context with session and fare source code

        Returns:
            Domain FlightRevalidateResponse

        Raises:
            ConversionError: If required data is missing
        """
        if dto.Errors:
            return FlightRevalidateResponse(
                session_id="",  # Required field
                fare_source_code="",  # Required field
                return_fare_source_code=None,  # Required field for schema validation
                is_fare_available=False,  # Required field
                validated_fare_itineraries=[],  # Required field
                available_extra_services=None,  # Required field for schema validation
                errors=[self._convert_error(dto.Errors, context)],
            )

        if not dto.AirRevalidateResponse:
            raise ConversionError(
                "No AirRevalidateResponse in FlightLogic response",
                source_data=dto,
                target_type=FlightRevalidateResponse,
            )

        response_data = dto.AirRevalidateResponse
        result = response_data.AirRevalidateResult

        # Log essential revalidate info only (reduced verbosity)
        is_valid = getattr(result, "IsValid", False)
        sequence_num = (
            str(getattr(result, "SequenceNumber", "N/A"))[:10]
            if hasattr(result, "SequenceNumber") and result.SequenceNumber is not None
            else "N/A"
        )
        self.logger.info(
            f"Revalidate API response - Valid: {is_valid}, Sequence: {sequence_num}..."
        )

        # Check if fare is valid
        is_valid = self._parse_boolean_value(result.IsValid)

        # Log detailed error information when revalidation fails
        if not is_valid:
            error_code = getattr(result, "ErrorCode", "Unknown")
            error_message = getattr(result, "ErrorMessage", "No error message provided")
            warnings = getattr(result, "Warnings", [])

            self.logger.error(
                f"FlightLogic revalidation failed - "
                f"ErrorCode: {error_code}, ErrorMessage: {error_message}, "
                f"Warnings: {warnings if warnings else 'None'}"
            )

        # Create or update context
        if not context:
            context = ConversionContext()

        validated_fare_itineraries = []
        if is_valid and result.FareItineraries:
            # Convert FareItineraries dict to validated itinerary
            validated_itinerary = self._convert_validated_fare_itinerary(
                result.FareItineraries
            )
            validated_fare_itineraries.append(validated_itinerary)

            # Extract sequence number from validated itinerary for session tracking
            if validated_itinerary.sequence_number:
                context.session_id = validated_itinerary.sequence_number

        # Process inbound result for Indian domestic roundtrips
        if response_data.AirRevalidateResultInbound:
            inbound_result = response_data.AirRevalidateResultInbound
            if (
                self._parse_boolean_value(inbound_result.IsValid)
                and inbound_result.FareItineraries
            ):
                inbound_itinerary = self._convert_validated_fare_itinerary(
                    inbound_result.FareItineraries
                )
                validated_fare_itineraries.append(inbound_itinerary)

        # Revalidate summary logged above with API sequence number

        # Convert available extra services
        available_services = None
        if result.ExtraServices:
            available_services = self._convert_extra_services_from_revalidate(
                result.ExtraServices
            )

        return FlightRevalidateResponse(
            session_id=context.session_id if context and context.session_id else "",
            fare_source_code=context.fare_source_code
            if context and context.fare_source_code
            else "",
            return_fare_source_code=context.inbound_fare_source_code
            if context and context.inbound_fare_source_code
            else None,
            is_fare_available=is_valid,
            validated_fare_itineraries=validated_fare_itineraries,
            available_extra_services=available_services,
            errors=None,
        )

    @staticmethod
    def _parse_boolean_value(value: bool | str | None) -> bool:
        """Parse boolean value from various formats."""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "true"
        return False

    def _convert_extra_services_from_revalidate(
        self, services_data: dict[str, Any]
    ) -> AvailableExtraServices:
        """Convert extra services from revalidate response."""
        service_options = []

        if services_data:
            # Check for dynamic services (baggage, meals, seats)
            # The structure varies depending on what's available

            # Parse baggage services if present
            if "DynamicBaggage" in services_data:
                for baggage_data in services_data["DynamicBaggage"]:
                    if isinstance(baggage_data, dict):
                        service_options.append(
                            self._convert_baggage_service_category(
                                DynamicService(**baggage_data)
                            )
                        )

            # Parse meal services if present
            if "DynamicMeal" in services_data:
                for meal_data in services_data["DynamicMeal"]:
                    if isinstance(meal_data, dict):
                        service_options.append(
                            self._convert_meal_service_category(
                                DynamicService(**meal_data)
                            )
                        )

            # Parse seat services if present
            if "DynamicSeat" in services_data:
                seat_categories = self._convert_seat_services(
                    services_data["DynamicSeat"]
                )
                service_options.extend(seat_categories)

        return AvailableExtraServices(service_options=service_options)

    # ============================================================
    # BOOKING REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def booking_request_to_dto(
        self, request: FlightBookingRequest
    ) -> FlightLogicBookingRequest:
        """Convert domain booking request to FlightLogic DTO."""

        # Helper function to extract area code from phone number
        def _extract_area_code(phone: str) -> str:
            """Extract area code from international phone number.

            FlightLogic requires area code, so we extract it from the full phone number.
            Raises ConversionError if extraction fails.
            """
            try:
                from phonenumbers import PhoneNumberFormat, format_number
                from phonenumbers import parse as parse_phone

                # Try parsing with US as default region for local numbers
                parsed = parse_phone(phone, "US")
                # Format as national and extract area code
                national = format_number(parsed, PhoneNumberFormat.NATIONAL)
                # Extract digits after country code but before local number
                import re

                area_match = re.search(r"\(?(\d{2,4})\)?[-\s]", national)
                if area_match:
                    return area_match.group(1)

                raise ConversionError(
                    f"Could not extract area code from phone number: {phone}",
                    {"phone": phone, "national_format": national},
                )
            except (ValueError, TypeError, AttributeError) as e:
                raise ConversionError(
                    f"Invalid phone number format: {phone}",
                    {"phone": phone, "error": str(e)},
                ) from e

        def _extract_country_code(phone: str) -> str:
            """Extract country code from international phone number.

            Returns the numeric country code (e.g., '1' for US, '31' for NL).
            FlightLogic expects numeric country codes, not ISO codes.
            Raises ConversionError if extraction fails.
            """
            try:
                from phonenumbers import parse as parse_phone

                # Try parsing with US as default region for local numbers
                parsed = parse_phone(phone, "US")
                return str(parsed.country_code)
            except (ValueError, TypeError, AttributeError) as e:
                raise ConversionError(
                    f"Invalid phone number format: {phone}",
                    {"phone": phone, "error": str(e)},
                ) from e

        # Convert passenger details
        # FlightLogic expects ONE PaxDetails object with all passengers aggregated by type
        # Each field must be an array with one value per passenger of that type

        import logging

        logger = logging.getLogger(__name__)

        # Aggregate adults into arrays
        dto_adult = None
        if request.passenger_groups.adults:
            adults = request.passenger_groups.adults
            logger.info(f"DEBUG: Aggregating {len(adults)} adults into array format")

            dto_adult = DtoAdultPassenger(
                title=[a.personal_info.name.title for a in adults],
                firstName=[a.personal_info.name.first_name for a in adults],
                lastName=[a.personal_info.name.last_name for a in adults],
                dob=[a.personal_info.date_of_birth for a in adults],
                nationality=[
                    a.personal_info.nationality if a.personal_info.nationality else ""
                    for a in adults
                ],
            )

            # Aggregate passport details if any adult has them
            if any(
                a.travel_documents and a.travel_documents.passport_number
                for a in adults
            ):
                dto_adult.passportNo = [
                    a.travel_documents.passport_number if a.travel_documents else None
                    for a in adults
                ]
                dto_adult.passportIssueCountry = [
                    a.travel_documents.passport_country if a.travel_documents else None
                    for a in adults
                ]
                dto_adult.passportExpiryDate = [
                    a.travel_documents.passport_expiry if a.travel_documents else None
                    for a in adults
                ]

            # Aggregate frequent flyer numbers if any
            if any(a.frequent_flyer_info for a in adults):
                dto_adult.frequentFlyrNum = [
                    a.frequent_flyer_info.member_number
                    if a.frequent_flyer_info
                    else None
                    for a in adults
                ]

            # Aggregate service selections
            if any(a.service_selections for a in adults):
                dto_adult.ExtraServiceOutbound = []
                dto_adult.ExtraServiceInbound = []
                for adult in adults:
                    if (
                        adult.service_selections
                        and adult.service_selections.outbound_services
                    ):
                        dto_adult.ExtraServiceOutbound.append(
                            [
                                s.service_id
                                for s in adult.service_selections.outbound_services
                            ]
                        )
                    else:
                        dto_adult.ExtraServiceOutbound.append([])

                    if (
                        adult.service_selections
                        and adult.service_selections.inbound_services
                    ):
                        dto_adult.ExtraServiceInbound.append(
                            [
                                s.service_id
                                for s in adult.service_selections.inbound_services
                            ]
                        )
                    else:
                        dto_adult.ExtraServiceInbound.append([])

        # Aggregate children into arrays
        dto_child = None
        if request.passenger_groups.children:
            children = request.passenger_groups.children
            logger.info(
                f"DEBUG: Aggregating {len(children)} children into array format"
            )

            dto_child = DtoChildPassenger(
                title=[c.personal_info.name.title for c in children],
                firstName=[c.personal_info.name.first_name for c in children],
                lastName=[c.personal_info.name.last_name for c in children],
                dob=[c.personal_info.date_of_birth for c in children],
                nationality=[
                    c.personal_info.nationality if c.personal_info.nationality else ""
                    for c in children
                ],
            )

            # Aggregate passport details if any child has them
            if any(
                c.travel_documents and c.travel_documents.passport_number
                for c in children
            ):
                dto_child.passportNo = [
                    c.travel_documents.passport_number if c.travel_documents else None
                    for c in children
                ]
                dto_child.passportIssueCountry = [
                    c.travel_documents.passport_country if c.travel_documents else None
                    for c in children
                ]
                dto_child.passportExpiryDate = [
                    c.travel_documents.passport_expiry if c.travel_documents else None
                    for c in children
                ]

            # Aggregate service selections
            if any(c.service_selections for c in children):
                dto_child.ExtraServiceOutbound = []
                dto_child.ExtraServiceInbound = []
                for child in children:
                    if (
                        child.service_selections
                        and child.service_selections.outbound_services
                    ):
                        dto_child.ExtraServiceOutbound.append(
                            [
                                s.service_id
                                for s in child.service_selections.outbound_services
                            ]
                        )
                    else:
                        dto_child.ExtraServiceOutbound.append([])

                    if (
                        child.service_selections
                        and child.service_selections.inbound_services
                    ):
                        dto_child.ExtraServiceInbound.append(
                            [
                                s.service_id
                                for s in child.service_selections.inbound_services
                            ]
                        )
                    else:
                        dto_child.ExtraServiceInbound.append([])

        # Aggregate infants into arrays
        dto_infant = None
        if request.passenger_groups.infants:
            infants = request.passenger_groups.infants
            logger.info(f"DEBUG: Aggregating {len(infants)} infants into array format")

            dto_infant = DtoInfantPassenger(
                title=[i.personal_info.name.title for i in infants],
                firstName=[i.personal_info.name.first_name for i in infants],
                lastName=[i.personal_info.name.last_name for i in infants],
                dob=[i.personal_info.date_of_birth for i in infants],
                nationality=[
                    i.personal_info.nationality if i.personal_info.nationality else ""
                    for i in infants
                ],
            )

            # Aggregate passport details if any infant has them
            if any(
                i.travel_documents and i.travel_documents.passport_number
                for i in infants
            ):
                dto_infant.passportNo = [
                    i.travel_documents.passport_number if i.travel_documents else None
                    for i in infants
                ]
                dto_infant.passportIssueCountry = [
                    i.travel_documents.passport_country if i.travel_documents else None
                    for i in infants
                ]
                dto_infant.passportExpiryDate = [
                    i.travel_documents.passport_expiry if i.travel_documents else None
                    for i in infants
                ]

        # Create single PaxDetails object with all passenger types
        pax_details = [PaxDetails(adult=dto_adult, child=dto_child, infant=dto_infant)]

        logger.info(
            f"DEBUG: Created single PaxDetails with adults={dto_adult is not None}, children={dto_child is not None}, infants={dto_infant is not None}"
        )

        # Build FlightBookingInfo
        # Validate required contact information
        if not request.contact_information.phone:
            raise ConversionError(
                "Phone number is required for booking",
                {"contact_info": request.contact_information},
            )

        phone_number = request.contact_information.phone
        country_code = _extract_country_code(phone_number)
        area_code = _extract_area_code(phone_number)

        flight_booking_info = FlightBookingInfo(
            flight_session_id=request.session_id,
            fare_source_code=request.fare_source_code,
            IsPassportMandatory="true" if request.requires_passport else "false",
            fareType=request.fare_type.value,
            payment_id=request.payment_id,  # Pass payment_id to control booking vs ticket issuance
            areaCode=area_code,
            countryCode=country_code,
            fare_source_code_inbound=request.inbound_fare_source_code,
        )

        # Build PaxInfo
        # Validate email
        if not request.contact_information.email:
            raise ConversionError(
                "Email is required for booking",
                {"contact_info": request.contact_information},
            )

        pax_info = PaxInfo(
            clientRef=request.client_reference,
            postCode=request.postal_code.code if request.postal_code else None,
            customerEmail=str(request.contact_information.email),
            customerPhone=phone_number,
            bookingNote=request.booking_notes.instructions
            if request.booking_notes
            else None,
            paxDetails=pax_details,
        )

        # Debug: Log pax_details AFTER creating PaxInfo
        logger.info(f"DEBUG: pax_info.paxDetails count: {len(pax_info.paxDetails)}")
        logger.info(f"DEBUG: pax_info model_dump: {pax_info.model_dump(by_alias=True)}")

        return FlightLogicBookingRequest(
            flightBookingInfo=flight_booking_info,
            paxInfo=pax_info,
        )

    def booking_response_from_dto(
        self, dto: FlightLogicBookingResponse
    ) -> FlightBookingResponse:
        """Convert FlightLogic booking response DTO to domain schema.

        Raises:
            ConversionError: If required data is missing
        """
        if dto.Errors:
            # Create context for booking error
            error_context = ConversionContext(
                original_request=None,  # Would be populated if available
                supplier="FlightLogic",
            )
            return FlightBookingResponse(
                booking_status=BookingStatus.FAILED,  # Required field
                is_successful=False,  # Required field
                external_booking_reference="",  # Required field
                ticket_time_limit=None,  # Required field for schema validation
                environment=FlightAPIEnvironment.TEST,  # Required field
                errors=[
                    self._convert_error(dto.Errors, error_context)
                ],  # Required field
            )

        if not dto.BookFlightResponse:
            raise ConversionError(
                "No BookFlightResponse in FlightLogic response",
                source_data=dto,
                target_type=FlightBookingResponse,
            )

        result = dto.BookFlightResponse.BookFlightResult

        # Determine success
        is_successful = self._parse_boolean_value(result.Success)

        # Determine booking status
        booking_status = FlightLogicSchemaAdapter._parse_booking_status(
            result.Status, is_successful
        )

        # Parse ticket time limit
        ticket_time_limit = None
        if result.TktTimeLimit:
            with contextlib.suppress(Exception):
                # Log warning but don't fail the conversion
                # Ticket time limit is optional
                ticket_time_limit = DateTime(
                    value=_parse_datetime_string(result.TktTimeLimit)
                )

        # Determine environment
        api_environment = self._parse_api_environment(result.Target)

        # Booking reference is REQUIRED for successful bookings
        # If Success=true but no UniqueID, the booking actually failed
        if not result.UniqueID:
            if is_successful:
                # Success=true but no UniqueID means API inconsistency - treat as failure
                logger.error(
                    f"FlightLogic returned Success=true but no UniqueID. Status: {result.Status}. "
                    "This indicates a booking failure despite success flag."
                )
                is_successful = False
                booking_status = BookingStatus.FAILED
            else:
                # Already marked as unsuccessful, create error response
                logger.error("Booking failed: No UniqueID in FlightLogic response")

            # Prefer provider error message (e.g. "Booking already done with Current Session ID")
            error_context = ConversionContext(
                original_request=None,
                supplier="FlightLogic",
            )
            provider_error = self._booking_result_error_to_details(
                result, error_context
            )
            if provider_error:
                errors_list = [provider_error]
            else:
                errors_list = [
                    ErrorDetails(
                        code="MISSING_BOOKING_REFERENCE",
                        message="FlightLogic did not return a booking reference. Booking failed.",
                        details={
                            "status": result.Status,
                            "success_flag": str(result.Success),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                ]

            return FlightBookingResponse(
                booking_status=BookingStatus.FAILED,
                is_successful=False,
                external_booking_reference="",
                airline_pnr=None,
                ticket_time_limit=None,
                environment=api_environment,
                errors=errors_list,
            )

        # Try to extract PNR if available (may not be available immediately after booking)
        result_dict = (
            result.model_dump()
            if hasattr(result, "model_dump")
            else (result.__dict__ if hasattr(result, "__dict__") else {})
        )

        # Log raw response for PNR debugging
        logger.debug(f"FlightLogic booking response fields: {list(result_dict.keys())}")
        if "PNR" in result_dict:
            logger.info(f"Found PNR in booking response: {result_dict['PNR']}")
        else:
            logger.warning(
                f"No PNR field in booking response. Available fields: {list(result_dict.keys())}"
            )

        airline_pnr = self._extract_airline_pnr(None, result_dict, None)

        if airline_pnr:
            logger.info(
                f"Extracted airline PNR: code={airline_pnr.pnr_code}, airline={airline_pnr.airline.iata_code if airline_pnr.airline else 'None'}"
            )
        else:
            logger.warning("Failed to extract airline PNR from booking response")

        return FlightBookingResponse(
            booking_status=booking_status,
            is_successful=is_successful,
            external_booking_reference=result.UniqueID,
            airline_pnr=airline_pnr,
            ticket_time_limit=ticket_time_limit,
            environment=api_environment,
            errors=[],
        )

    @staticmethod
    def _parse_booking_status(
        status: str | dict | None, is_successful: bool = True
    ) -> BookingStatus:
        """Parse booking status from response.

        Args:
            status: Can be either:
                - A string like "CONFIRMED", "PENDING" (from booking response)
                - A dict to extract status from (from trip details response)
            is_successful: Whether the operation was successful (used as fallback)

        Returns:
            BookingStatus enum value
        """
        # If it's a dict, extract the status string first
        if isinstance(status, dict):
            status = status.get("Status", status.get("BookingStatus", "confirmed"))

        # Now handle the string
        if not status:
            return BookingStatus.PENDING if is_successful else BookingStatus.FAILED

        status_upper = str(status).upper()
        if status_upper == "CONFIRMED" or "CONFIRM" in status_upper:
            return BookingStatus.CONFIRMED
        if status_upper == "PENDING" or "PENDING" in status_upper:
            return BookingStatus.PENDING
        if (
            status_upper == "FAILED"
            or "FAIL" in status_upper
            or "CANCEL" in status_upper
        ):
            return BookingStatus.FAILED

        # Default based on success flag
        return BookingStatus.CONFIRMED if is_successful else BookingStatus.FAILED

    @staticmethod
    def _parse_api_environment(target: str | None) -> FlightAPIEnvironment:
        """Parse API environment from target string."""
        if not target:
            return FlightAPIEnvironment.TEST
        if target.lower() == "production":
            return FlightAPIEnvironment.PRODUCTION
        return FlightAPIEnvironment.TEST

    # ============================================================
    # CANCELLATION REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def cancel_request_to_dto(
        self, request: FlightCancelRequest
    ) -> FlightLogicCancelRequest:
        """Convert domain cancel request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        return FlightLogicCancelRequest(
            user_id=user_id,
            user_password=user_password,
            access=environment,
            ip_address=ip_address,
            UniqueID=request.external_booking_reference,
        )

    def cancel_response_from_dto(
        self, dto: FlightLogicCancelResponse
    ) -> FlightCancelResponse:
        """Convert FlightLogic cancel response DTO to domain schema."""
        if dto.Errors:
            # Create context for cancel error
            error_context = ConversionContext(supplier="FlightLogic")
            return FlightCancelResponse(
                success=False,  # Required field
                external_booking_reference=None,  # Required field for schema validation
                errors=[
                    self._convert_error(dto.Errors, error_context)
                ],  # Required field
            )

        if not dto.CancelBookingResponse:
            raise ConversionError(
                "No CancelBookingResponse in FlightLogic response",
                source_data=dto,
                target_type=FlightCancelResponse,
            )

        result = dto.CancelBookingResponse.CancelBookingResult

        # Determine success
        success = (
            result.Success.lower() == "true"
            if isinstance(result.Success, str)
            else False
        )

        # UniqueID might not be returned on failure
        external_booking_reference = result.UniqueID if result.UniqueID else None

        return FlightCancelResponse(
            success=success,
            external_booking_reference=external_booking_reference,
            errors=[],
        )

    # ==========================================================
    # EXTRA SERVICES REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def extra_services_request_to_dto(
        self, request: FlightExtraServicesRequest
    ) -> FlightLogicExtraServicesRequest:
        """Convert domain extra services request to FlightLogic DTO."""
        return FlightLogicExtraServicesRequest(
            session_id=request.session_id,
            fare_source_code=request.fare_source_code,
        )

    def extra_services_response_from_dto(
        self,
        dto: FlightLogicExtraServicesResponse,
        context: ConversionContext | None = None,
    ) -> FlightExtraServicesResponse:
        """Convert FlightLogic extra services response DTO to domain schema."""
        if dto.Errors:
            return FlightExtraServicesResponse(
                session_id="",  # Required field
                fare_source_code="",  # Required field
                is_successful=False,  # Required field
                extra_services_data=ExtraServicesData(
                    baggage_services=None,
                    meal_services=None,
                    seat_services=None,
                ),  # Required field
                errors=[self._convert_error(dto.Errors, context)],
            )

        if not dto.ExtraServicesResponse:
            raise ConversionError(
                "No ExtraServicesResponse in FlightLogic response",
                source_data=dto,
                target_type=FlightExtraServicesResponse,
            )

        result = dto.ExtraServicesResponse.ExtraServicesResult
        services_data = result.ExtraServicesData

        # Convert baggage services
        baggage_services = []
        if services_data and services_data.DynamicBaggage:
            for dynamic_service in services_data.DynamicBaggage:
                baggage_category = self._convert_baggage_service_category(
                    dynamic_service
                )
                baggage_services.append(baggage_category)

        # Convert meal services
        meal_services = []
        if services_data and services_data.DynamicMeal:
            for dynamic_service in services_data.DynamicMeal:
                meal_category = self._convert_meal_service_category(dynamic_service)
                meal_services.append(meal_category)

        # Convert seat services (complex structure, simplified for now)
        seat_services = []

        return FlightExtraServicesResponse(
            session_id=context.session_id if context else None,
            fare_source_code=context.fare_source_code if context else None,
            is_successful=result.success,
            extra_services_data=ExtraServicesData(
                baggage_services=baggage_services if baggage_services else None,
                meal_services=meal_services if meal_services else None,
                seat_services=seat_services if seat_services else None,
            ),
            errors=None,
        )

    # ============================================================
    # FARE RULES REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def fare_rules_request_to_dto(
        self, request: FlightFareRulesRequest
    ) -> FlightLogicFareRulesRequest:
        """Convert domain fare rules request to FlightLogic DTO."""
        return FlightLogicFareRulesRequest(
            session_id=request.session_id,
            fare_source_code=request.fare_source_code,
            fare_source_code_inbound=request.inbound_fare_source_code,
        )

    def fare_rules_response_from_dto(
        self,
        dto: FlightLogicFareRulesResponse,
        context: ConversionContext | None = None,
    ) -> FlightFareRulesResponse:
        """Convert FlightLogic fare rules response DTO to domain schema."""
        if dto.Errors:
            return FlightFareRulesResponse(
                session_id="",  # Required field
                fare_source_code="",  # Required field
                baggage_information=[],  # Required field
                fare_rules=[],  # Required field
                inbound_fare_data=None,  # Required field for schema validation
                errors=[self._convert_error(dto.Errors, context)],
            )

        if not dto.FareRules1_1Response:
            raise ConversionError(
                "No FareRules1_1Response in FlightLogic response",
                source_data=dto,
                target_type=FlightFareRulesResponse,
            )

        response_data = dto.FareRules1_1Response
        result = response_data.FareRules1_1Result

        # Convert baggage information
        baggage_information = []
        if result.BaggageInfos:
            for baggage_dict in result.BaggageInfos:
                for _key, baggage_info in baggage_dict.items():
                    baggage_information.append(
                        self._convert_baggage_information(baggage_info)
                    )

        # Convert fare rules
        fare_rules = []
        if result.FareRules:
            for rule_dict in result.FareRules:
                for _key, fare_rule in rule_dict.items():
                    fare_rules.append(self._convert_fare_rule_details(fare_rule))

        # Convert inbound data if present
        inbound_fare_data = None
        if response_data.FareRules1_1ResultInbound:
            inbound_result = response_data.FareRules1_1ResultInbound
            inbound_baggage = []
            inbound_rules = []

            if inbound_result.BaggageInfos:
                for baggage_dict in inbound_result.BaggageInfos:
                    for _key, baggage_info in baggage_dict.items():
                        inbound_baggage.append(
                            self._convert_baggage_information(baggage_info)
                        )

            if inbound_result.FareRules:
                for rule_dict in inbound_result.FareRules:
                    for _key, fare_rule in rule_dict.items():
                        inbound_rules.append(self._convert_fare_rule_details(fare_rule))

            inbound_fare_data = InboundFareData(
                baggage_information=inbound_baggage,
                fare_rules=inbound_rules,
            )

        return FlightFareRulesResponse(
            session_id=context.session_id if context else "",
            fare_source_code=context.fare_source_code if context else "",
            baggage_information=baggage_information,
            fare_rules=fare_rules,
            inbound_fare_data=inbound_fare_data,
            errors=None,
        )

    # ============================================================
    # TRIP DETAILS REQUEST/RESPONSE ADAPTERS
    # ============================================================

    def trip_details_request_to_dto(
        self, request: TripDetailsRequest
    ) -> FlightLogicTripDetailsRequest:
        """Convert domain trip details request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        return FlightLogicTripDetailsRequest(
            user_id=user_id,
            user_password=user_password,
            access=environment,
            ip_address=ip_address,
            UniqueID=request.external_booking_reference,
        )

    def trip_details_response_from_dto(
        self, dto: FlightLogicTripDetailsResponse
    ) -> TripDetailsResponse:
        """Convert FlightLogic trip details response DTO to domain schema.

        Parses the actual FlightLogic response structure intelligently.
        """
        # Check for errors first before attempting to parse
        if dto.Errors:
            error_context = ConversionContext(supplier="FlightLogic")
            return TripDetailsResponse(
                success=False,
                booking_status=BookingStatus.FAILED,
                cross_border_indicator=False,
                destination=AirportInfo(
                    iata_code="UNK", airport_name="Unknown", city_name="Unknown"
                ),
                origin=AirportInfo(
                    iata_code="UNK", airport_name="Unknown", city_name="Unknown"
                ),
                fare_type=FareType.PUBLIC,
                is_commissionable=False,
                is_mo_fare=False,
                external_booking_reference="",
                ticket_status=TicketStatus.NOT_ISSUED,
                environment=FlightAPIEnvironment.TEST,
                passengers=[],
                segments=[],
                pricing=None,
                fare_breakdown=[],
                extra_services=[],
                booking_notes=[],
                errors=[self._convert_error(dto.Errors, error_context)],
            )

        return self._parse_trip_details_response(dto)

    def ticket_request_to_dto(
        self, request: TicketOrderRequest
    ) -> FlightLogicTicketRequest:
        """Convert domain ticket request to FlightLogic DTO.

        Automatically injects FlightLogic credentials from config if not provided.
        """
        # Get credentials (from request or config)
        user_id, user_password, environment, ip_address = self._inject_credentials(
            request
        )

        return FlightLogicTicketRequest(
            user_id=user_id,
            user_password=user_password,
            access=environment,
            ip_address=ip_address,
            UniqueID=request.external_booking_reference,
        )

    def ticket_response_from_dto(
        self, dto: FlightLogicTicketResponse
    ) -> TicketOrderResponse:
        """Convert FlightLogic ticket response DTO to domain schema."""
        if dto.Errors:
            # Create context for ticket error
            error_context = ConversionContext(supplier="FlightLogic")
            return TicketOrderResponse(
                success=False,  # Required field
                external_booking_reference="",  # Required field
                environment=FlightAPIEnvironment.TEST,  # Required field
                errors=[
                    self._convert_error(dto.Errors, error_context)
                ],  # Required field
            )

        if not dto.AirOrderTicketRS:
            raise ConversionError(
                "No AirOrderTicketRS in FlightLogic response",
                source_data=dto,
                target_type=TicketOrderResponse,
            )

        result = dto.AirOrderTicketRS.TicketOrderResult

        # Determine success - handle both string "true" and boolean True
        if isinstance(result.Success, str):
            success = result.Success.lower() == "true"
        elif isinstance(result.Success, bool):
            success = result.Success
        else:
            success = False

        # When success is false, populate errors from TicketOrderResult.Errors if present
        errors_list: list[ErrorDetails] = []
        if not success and result.Errors:
            error_context = ConversionContext(supplier="FlightLogic")
            err_raw = (
                result.Errors.get("Error")
                if isinstance(result.Errors, dict)
                else result.Errors
            )
            if err_raw:
                errors_list = [self._convert_error(err_raw, error_context)]

        # Determine environment
        environment = FlightAPIEnvironment.TEST
        if result.Target == "Production":
            environment = FlightAPIEnvironment.PRODUCTION

        # FlightLogic reference - UniqueID is optional per FlightLogic API docs
        # Use empty string if not provided (happens in some responses)
        external_booking_reference = result.UniqueID if result.UniqueID else ""

        return TicketOrderResponse(
            success=success,
            external_booking_reference=external_booking_reference,
            environment=environment,
            errors=errors_list,
        )

    # ============================================================
    # HELPER METHODS
    # ============================================================

    @staticmethod
    def _has_errors(dto: Any) -> bool:
        """Check if DTO contains errors.

        Returns True if errors are present and not empty.
        """
        if not hasattr(dto, "Errors"):
            return False

        errors = dto.Errors

        # Check various forms of "no error"
        # Return True if we have errors, False otherwise
        return not (
            errors is None or errors == "" or (isinstance(errors, dict) and not errors)
        )

    def _booking_result_error_to_details(
        self,
        result: Any,
        context: ConversionContext | None = None,
    ) -> ErrorDetails | None:
        """Extract FlightLogic error from BookFlightResult.Errors for user-facing message.

        Handles nested shape: Errors.Error.ErrorCode / Errors.Error.ErrorMessage.
        Returns None if no usable error is found.
        """
        errors_raw = getattr(result, "Errors", None)
        if not errors_raw or not isinstance(errors_raw, dict):
            return None
        # Nested: {"Error": {"ErrorCode": "...", "ErrorMessage": "..."}}
        err = errors_raw.get("Error") or errors_raw
        if not isinstance(err, dict):
            return None
        if not (err.get("ErrorCode") or err.get("ErrorMessage")):
            return None
        return self._convert_error(err, context)

    def _convert_error(
        self,
        error: FlightLogicError | dict | str | Any,
        context: ConversionContext | None = None,
    ) -> ErrorDetails:
        """Convert FlightLogic error to domain error with systematic categorization.

        Handles various error formats that FlightLogic might return:
        - FlightLogicError object with ErrorCode and ErrorMessage
        - Dict with error details
        - String error message
        - Other formats

        Args:
            error: The error data from FlightLogic
            context: Optional context for additional error details

        Returns:
            ErrorDetails with proper categorization and context

        Raises:
            ConversionError: If error format is unrecognized or missing required fields
        """
        original_error = error

        # Extract error code and message based on error type
        if hasattr(error, "ErrorCode") and hasattr(error, "ErrorMessage"):
            error_code = error.ErrorCode
            error_message = error.ErrorMessage
        elif isinstance(error, dict):
            error_code = error.get("ErrorCode") or error.get("error_code")
            error_message = error.get("ErrorMessage") or error.get("error_message")

            if not error_code:
                self.logger.warning(f"FlightLogic error without error code: {error}")
                error_code = "API_ERROR"

            if not error_message:
                self.logger.warning(f"FlightLogic error without error message: {error}")
                error_message = "API returned an error without details"

            if not (error.get("ErrorCode") or error.get("error_code")) and not (
                error.get("ErrorMessage") or error.get("error_message")
            ):
                raise ConversionError(
                    f"Error dict missing required fields: {error}",
                    source_data=error,
                    target_type=ErrorDetails,
                )
        elif isinstance(error, str) and error.strip():
            # Extract error code if present in string format like "ERR001: Message"
            if ":" in error:
                parts = error.split(":", 1)
                error_code = parts[0].strip()
                error_message = parts[1].strip()
            else:
                error_code = "FLIGHTLOGIC_ERROR"
                error_message = error
        else:
            # For any other type or None, create a generic error
            error_code = "UNKNOWN_ERROR"
            error_message = f"Unknown error of type {type(error).__name__}: {error}"

        # Build error details with context and category
        error_details = FlightLogicSchemaAdapter._build_error_details(
            original_error, context
        )

        # Add error category to details
        error_category = self._categorize_error(error_code, error_message)
        error_details["error_category"] = error_category

        return ErrorDetails(
            code=error_code,
            message=error_message,
            details=error_details,
        )

    @staticmethod
    def _categorize_error(error_code: str, error_message: str) -> str:
        """Systematically categorize FlightLogic errors based on code and message.

        Args:
            error_code: The error code from FlightLogic
            error_message: The error message from FlightLogic

        Returns:
            Standardized error category
        """
        error_code_upper = error_code.upper()
        error_message_upper = error_message.upper()

        # Authentication and authorization errors
        if any(
            keyword in error_code_upper
            for keyword in ["AUTH", "LOGIN", "CREDENTIAL", "TOKEN"]
        ):
            return "AUTHENTICATION_ERROR"
        if any(
            keyword in error_message_upper
            for keyword in [
                "INVALID CREDENTIAL",
                "AUTHENTICATION",
                "UNAUTHORIZED",
                "LOGIN",
            ]
        ):
            return "AUTHENTICATION_ERROR"

        # Validation errors
        if any(
            keyword in error_code_upper
            for keyword in ["VALIDATION", "INVALID", "REQUIRED", "MISSING"]
        ):
            return "VALIDATION_ERROR"
        if any(
            keyword in error_message_upper
            for keyword in ["INVALID", "REQUIRED", "MISSING", "VALIDATION", "FORMAT"]
        ):
            return "VALIDATION_ERROR"

        # Booking-specific errors
        if any(
            keyword in error_code_upper
            for keyword in ["BOOKING", "FARE", "AVAILABILITY", "SOLD"]
        ):
            return "BOOKING_ERROR"
        if any(
            keyword in error_message_upper
            for keyword in ["BOOKING", "FARE", "NOT AVAILABLE", "SOLD OUT", "INVENTORY"]
        ):
            return "BOOKING_ERROR"

        # Search-specific errors
        if any(
            keyword in error_code_upper
            for keyword in ["SEARCH", "NO_RESULT", "NORESULT"]
        ):
            return "SEARCH_ERROR"
        if any(
            keyword in error_message_upper
            for keyword in ["NO RESULT", "NO FLIGHTS", "SEARCH"]
        ):
            return "SEARCH_ERROR"

        # Network and timeout errors
        if any(
            keyword in error_code_upper
            for keyword in ["TIMEOUT", "NETWORK", "CONNECTION"]
        ):
            return "TIMEOUT_ERROR"
        if any(
            keyword in error_message_upper
            for keyword in ["TIMEOUT", "NETWORK", "CONNECTION", "UNAVAILABLE"]
        ):
            return "TIMEOUT_ERROR"

        # Rate limiting and API errors
        if any(
            keyword in error_code_upper for keyword in ["RATE", "LIMIT", "QUOTA", "API"]
        ):
            return "API_ERROR"
        if any(
            keyword in error_message_upper
            for keyword in ["RATE LIMIT", "QUOTA", "API ERROR", "SERVICE ERROR"]
        ):
            return "API_ERROR"

        # Default to unknown for unclassified errors
        return "UNKNOWN_ERROR"

    @staticmethod
    def _build_error_details(
        original_error: Any, context: ConversionContext | None
    ) -> dict[str, Any]:
        """Build comprehensive error details context.

        Args:
            original_error: The original error data from FlightLogic
            context: Optional conversion context

        Returns:
            Dictionary with error context and debugging information
        """
        details = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "source": "FlightLogic",
        }

        # Add context information if available
        if context:
            if context.session_id:
                details["session_id"] = context.session_id
            if context.fare_source_code:
                details["fare_source_code"] = context.fare_source_code
            if context.inbound_fare_source_code:
                details["inbound_fare_source_code"] = context.inbound_fare_source_code
            if context.supplier:
                details["supplier"] = context.supplier

        # Add original error data for debugging
        if original_error is not None:
            details["original_error_type"] = type(original_error).__name__

            # Safely serialize the original error
            try:
                if hasattr(original_error, "__dict__"):
                    # For objects, get their attributes
                    error_data: dict[str, Any] = {
                        key: str(value)
                        for key, value in original_error.__dict__.items()
                        if not key.startswith("_")
                    }
                    details["original_error_data"] = str(error_data)
                elif isinstance(original_error, dict | list | str | int | float | bool):
                    # For basic types, include directly
                    details["original_error_data"] = original_error
                else:
                    # For other types, convert to string
                    details["original_error_data"] = str(original_error)
            except (AttributeError, TypeError, ValueError):
                # If serialization fails, just note the type
                details["original_error_data"] = (
                    f"Error serializing {type(original_error).__name__}"
                )

        return details

    @staticmethod
    def _convert_money_amount(amount_info: AmountInfo | dict) -> MoneyAmount:
        """Convert AmountInfo or dict to MoneyAmount.

        For flight search responses - currency must be present in API response.
        """
        # Handle both AmountInfo objects and dicts
        if isinstance(amount_info, dict):
            amount = amount_info.get("Amount", 0)
            currency = amount_info.get("CurrencyCode")
            if not currency:
                raise ConversionError(
                    "Missing CurrencyCode in amount info", {"amount_info": amount_info}
                )
            decimal_places = amount_info.get("DecimalPlaces", 2)
        else:
            amount = amount_info.Amount
            currency = amount_info.CurrencyCode
            if not currency:
                raise ConversionError(
                    "Missing CurrencyCode in AmountInfo object",
                    {"amount_info": amount_info},
                )
            decimal_places = amount_info.DecimalPlaces

        # Convert decimal_places to int if it's a string
        if isinstance(decimal_places, str):
            decimal_places = int(decimal_places)

        # MoneyAmount expects amount as string, not float
        return MoneyAmount(
            amount=Decimal(str(amount)),
            currency=currency,
            decimal_places=decimal_places,
        )

    def _convert_flight_segment(
        self, segment: DtoFlightSegment, segment_option: dict[str, Any] | None = None
    ) -> FlightSegment:
        """Convert DTO flight segment to domain flight segment.

        Args:
            segment: DTO flight segment
            segment_option: Optional parent segment option with additional data

        Returns:
            Domain FlightSegment with all available data
        """
        # Convert datetime strings
        arrival_datetime = DateTime(
            value=_parse_datetime_string(segment.ArrivalDateTime)
        )
        departure_datetime = DateTime(
            value=_parse_datetime_string(segment.DepartureDateTime)
        )

        # Convert cabin class
        cabin_class = self._parse_cabin_class(segment.CabinClassCode)

        # Get or create airport info (using cache)
        arrival_airport = self._get_airport_info(segment.ArrivalAirportLocationCode)
        departure_airport = self._get_airport_info(segment.DepartureAirportLocationCode)

        # Get or create airline info (using cache)
        marketing_airline = self._get_airline_info(
            segment.MarketingAirlineCode, segment.MarketingAirlineName
        )
        operating_airline = self._get_airline_info(
            segment.OperatingAirline.Code, segment.OperatingAirline.Name
        )

        # Create flight numbers
        marketing_flight_number = FlightNumber(
            airline_prefix=segment.MarketingAirlineCode,
            flight_number=segment.FlightNumber,
            formatted_number=f"{segment.MarketingAirlineCode}{segment.FlightNumber}",
        )
        operating_flight_number = FlightNumber(
            airline_prefix=segment.OperatingAirline.Code,
            flight_number=segment.OperatingAirline.FlightNumber,
            formatted_number=f"{segment.OperatingAirline.Code}{segment.OperatingAirline.FlightNumber}",
        )

        # Get or create aircraft info (using cache)
        aircraft = self._get_aircraft_info(segment.OperatingAirline.Equipment)

        # Create duration
        journey_minutes = segment.JourneyDuration
        duration = Duration(
            total_minutes=journey_minutes,
        )

        # Convert meal code
        meal_code = self._parse_meal_code(segment.MealCode)

        # Convert marriage group
        marriage_group = self._parse_marriage_group(segment.MarriageGroup)

        # Extract segment stops and seat availability from segment_option if available
        segment_stops = 0
        seat_availability = None
        booking_class_code = None
        stop_details = None

        if segment_option:
            segment_stops_raw = segment_option.get("StopQuantity")
            if segment_stops_raw is None:
                raise ConversionError(
                    f"Missing StopQuantity for segment {segment.FlightNumber}",
                    source_data=segment_option,
                    target_type=FlightSegment,
                )
            segment_stops = int(segment_stops_raw)

            # Get seat availability
            seats_remaining = segment_option.get("SeatsRemaining")
            if seats_remaining:
                available_seats_raw = seats_remaining.get("Number")
                is_limited_raw = seats_remaining.get("BelowMinimum")

                if available_seats_raw is None or is_limited_raw is None:
                    raise ConversionError(
                        f"Missing seat availability data for segment {segment.FlightNumber}",
                        source_data=seats_remaining,
                        target_type=SeatAvailability,
                    )

                seat_availability = SeatAvailability(
                    available_seats=int(available_seats_raw),
                    is_limited=bool(is_limited_raw),
                )

            # Get booking class
            rbd_code = segment_option.get("ResBookDesigCode")
            if rbd_code:
                booking_class_code = BookingClassCode(
                    class_code=rbd_code,
                    class_name=segment_option.get("ResBookDesigText"),
                    fare_basis=None,  # Will be populated from fare breakdown if available
                )

            # Get stop details
            stop_info = segment_option.get("StopQuantityInfo")
            if stop_info and stop_info.get("LocationCode"):
                stop_details = [self._convert_stop_detail(stop_info)]

        # If no seat availability data, we must raise error as this is required
        if seat_availability is None:
            raise ConversionError(
                f"Missing seat availability data for segment {marketing_flight_number.formatted_number}",
                source_data=segment,
                target_type=FlightSegment,
            )

        return FlightSegment(
            arrival_airport=arrival_airport,
            arrival_datetime=arrival_datetime,
            departure_airport=departure_airport,
            departure_datetime=departure_datetime,
            cabin_class=cabin_class,
            cabin_class_text=self._parse_cabin_class_text(segment.CabinClassText),
            e_ticket=segment.Eticket,
            flight_duration=duration,
            marketing_flight_number=marketing_flight_number,
            marketing_airline=marketing_airline,
            marriage_group=marriage_group,
            meal_code=meal_code,
            operating_airline=operating_airline,
            operating_flight_number=operating_flight_number,
            aircraft=aircraft,
            booking_class_code=booking_class_code,
            segment_stops=segment_stops,
            stop_details=stop_details,
            seat_availability=seat_availability,
        )

    @staticmethod
    def _parse_cabin_class(code: str) -> CabinClass:
        """Parse cabin class from code."""
        cabin_class_map = {
            "Y": CabinClass.ECONOMY,
            "S": CabinClass.PREMIUM_ECONOMY,
            "C": CabinClass.BUSINESS,
            "F": CabinClass.FIRST,
        }
        result = cabin_class_map.get(code)
        if not result:
            raise ConversionError(
                f"Unknown cabin class code: {code}",
                source_data=code,
                target_type=CabinClass,
            )
        return result

    @staticmethod
    def _parse_optional_enum(value: str | None, enum_class: type) -> Any | None:
        """Generic parser for optional enum values.

        Args:
            value: The string value to parse
            enum_class: The enum class to parse into

        Returns:
            The enum value if parseable, None otherwise
        """
        if not value:
            return None
        try:
            return enum_class(value)
        except ValueError:
            return None

    @staticmethod
    def _parse_cabin_class_text(text: str | None) -> CabinClassText | None:
        """Parse cabin class text for LCC."""
        return FlightLogicSchemaAdapter._parse_optional_enum(text, CabinClassText)

    @staticmethod
    def _parse_meal_code(code: str | None) -> MealCode | None:
        """Parse meal code."""
        return FlightLogicSchemaAdapter._parse_optional_enum(code, MealCode)

    @staticmethod
    def _parse_marriage_group(group: str | None) -> MarriageGroup | None:
        """Parse marriage group indicator."""
        return FlightLogicSchemaAdapter._parse_optional_enum(group, MarriageGroup)

    @lru_cache(maxsize=1000)
    def _get_airport_info(self, iata_code: str) -> AirportInfo:
        """Get or create airport info with caching.

        In a real implementation, this would look up additional airport data
        from a database or API. For now, we only have the IATA code.
        """
        if iata_code in self._airport_cache:
            return self._airport_cache[iata_code]

        airport_info = AirportInfo(
            iata_code=iata_code,
            icao_code=None,  # Would be looked up from reference data
            airport_name=None,  # Would be looked up from reference data
            city_name=None,  # Would be looked up from reference data
            country_code=None,  # Would be looked up from reference data
        )
        self._airport_cache[iata_code] = airport_info
        return airport_info

    @lru_cache(maxsize=500)
    def _get_airline_info(self, iata_code: str, name: str | None = None) -> AirlineInfo:
        """Get or create airline info with caching and name resolution fallback."""
        from app.domains.airline import get_airline_name

        if iata_code in self._airline_cache:
            cached = self._airline_cache[iata_code]
            # Update name if we have it and cache doesn't
            if name and not cached.airline_name:
                cached.airline_name = name
            return cached

        # Try to resolve airline name if not provided
        resolved_name = name or get_airline_name(iata_code)

        airline_info = AirlineInfo(
            iata_code=iata_code,
            icao_code=None,  # Would be looked up from reference data
            airline_name=resolved_name,
        )
        self._airline_cache[iata_code] = airline_info
        return airline_info

    @lru_cache(maxsize=200)
    def _get_aircraft_info(self, type_code: str) -> AircraftInfo:
        """Get or create aircraft info with caching."""
        if type_code in self._aircraft_cache:
            return self._aircraft_cache[type_code]

        aircraft_info = AircraftInfo(
            aircraft_type_code=type_code,
            manufacturer=None,  # Would be looked up from reference data
            model_name=None,  # Would be looked up from reference data
        )
        self._aircraft_cache[type_code] = aircraft_info
        return aircraft_info

    def _convert_stop_detail(self, stop_info: dict[str, Any]) -> StopDetail:
        """Convert stop info to stop detail."""
        arrival_str = stop_info.get("ArrivalDateTime")
        departure_str = stop_info.get("DepartureDateTime")
        location_code = stop_info.get("LocationCode")

        if not location_code:
            raise ConversionError(
                "Missing LocationCode in stop info",
                source_data=stop_info,
                target_type=StopDetail,
            )

        # Calculate duration if both times are available
        duration = None
        if arrival_str and departure_str:
            try:
                arrival_dt = datetime.fromisoformat(arrival_str.replace("T", " "))
                departure_dt = datetime.fromisoformat(departure_str.replace("T", " "))
                duration_minutes = int((departure_dt - arrival_dt).total_seconds() / 60)
                if duration_minutes > 0:
                    duration = Duration(
                        total_minutes=duration_minutes,
                    )
            except (ValueError, TypeError, AttributeError):
                # Duration calculation failed, but it's optional
                pass

        return StopDetail(
            stop_airport=self._get_airport_info(location_code),
            arrival_time=DateTime(value=_parse_datetime_string(arrival_str))
            if arrival_str
            else None,
            departure_time=DateTime(value=_parse_datetime_string(departure_str))
            if departure_str
            else None,
            stop_duration=duration,
        )

    def _convert_fare_itinerary(self, fare_data: dict[str, Any]) -> FareItinerary:
        """Convert fare itinerary data to domain schema."""
        # Extract journey type (default to OneWay if not specified)
        journey_type_str = fare_data.get("DirectionInd", "OneWay")
        journey_type = JourneyType(journey_type_str)

        # Extract fare info
        fare_info = fare_data.get("AirItineraryFareInfo")
        if not fare_info:
            raise ConversionError(
                "Missing AirItineraryFareInfo in fare itinerary",
                source_data=fare_data,
                target_type=FareItinerary,
            )

        # Get fare type - required field
        fare_type_str = fare_info.get("FareType")
        if not fare_type_str:
            raise ConversionError(
                "Missing FareType in fare info", {"fare_info": fare_info}
            )
        # Map common fare type codes to enum values
        fare_type_map = {
            "PUB": FareType.PUBLIC,
            "Public": FareType.PUBLIC,
            "PRI": FareType.PRIVATE,
            "Private": FareType.PRIVATE,
            "WebFare": FareType.WEB_FARE,
            "WEB": FareType.WEB_FARE,
        }
        fare_type = fare_type_map.get(fare_type_str, FareType.PUBLIC)

        is_refundable_raw = fare_info.get("IsRefundable")
        if is_refundable_raw is None:
            raise ConversionError(
                "Missing IsRefundable in fare info",
                source_data=fare_info,
                target_type=FareItinerary,
            )
        is_refundable = bool(is_refundable_raw)
        fare_source_code = fare_info.get("FareSourceCode")
        if not fare_source_code:
            raise ConversionError(
                "Missing FareSourceCode in fare info",
                source_data=fare_info,
                target_type=FareItinerary,
            )

        # Convert fare totals
        itin_totals = fare_info.get("ItinTotalFares")
        if not itin_totals:
            raise ConversionError(
                "Missing ItinTotalFares in fare info",
                source_data=fare_info,
                target_type=FareItinerary,
            )

        if not itin_totals.get("BaseFare"):
            raise ConversionError(
                "Missing BaseFare in ItinTotalFares",
                source_data=itin_totals,
                target_type=FareTotals,
            )

        fare_totals = FareTotals(
            base_fare=self._convert_money_amount(itin_totals["BaseFare"]),
            equivalent_fare=self._convert_money_amount(itin_totals["EquivFare"])
            if itin_totals.get("EquivFare")
            else self._convert_money_amount(itin_totals["BaseFare"]),
            service_tax=self._convert_money_amount(itin_totals["ServiceTax"])
            if itin_totals.get("ServiceTax")
            else None,
            total_tax=self._convert_money_amount(itin_totals["TotalTax"])
            if itin_totals.get("TotalTax")
            else None,
            total_fare=self._convert_money_amount(itin_totals["TotalFare"])
            if itin_totals.get("TotalFare")
            else None,
        )

        # Convert passenger fare breakdown
        passenger_fare_breakdown = []
        for breakdown in fare_info.get("FareBreakdown", []):
            passenger_fare_breakdown.append(
                self._convert_passenger_fare_breakdown(breakdown)
            )

        # Always use FlightLogic's TotalFare - it is the authoritative source
        # The passenger breakdown can differ due to rounding or airline-specific calculations
        calculated_total_fare = sum(
            pax_breakdown.individual_passenger_fare.total_fare.amount
            * pax_breakdown.passenger_type_info.passenger_count
            for pax_breakdown in passenger_fare_breakdown
        )

        # Log mismatch for debugging purposes only - DO NOT override the API's TotalFare
        if (
            fare_totals.total_fare
            and abs(fare_totals.total_fare.amount - calculated_total_fare) > 0.01
        ):
            self.logger.debug(
                f"FlightLogic TotalFare ({fare_totals.total_fare.amount}) differs from calculated "
                f"breakdown sum ({calculated_total_fare:.2f}). Using API's TotalFare as authoritative."
            )

        # Create fare pricing
        has_mixed_booking_raw = fare_info.get("DivideInPartyIndicator")
        if has_mixed_booking_raw is None:
            raise ConversionError(
                "Missing DivideInPartyIndicator in fare info",
                source_data=fare_info,
                target_type=FarePricing,
            )

        pricing = FarePricing(
            has_mixed_booking_classes=bool(has_mixed_booking_raw),
            fare_source_code=fare_source_code,
            fare_type=fare_type,
            is_refundable=is_refundable,
            fare_totals=fare_totals,
            passenger_fare_breakdown=passenger_fare_breakdown,
        )

        # Convert flight legs
        flight_legs = []
        origin_dest_options = fare_data.get("OriginDestinationOptions", [])
        for option in origin_dest_options:
            segments = []
            total_stops_raw = option.get("TotalStops")
            if total_stops_raw is None:
                raise ConversionError(
                    "Missing TotalStops in origin destination option",
                    source_data=option,
                    target_type=FlightLeg,
                )
            total_stops = int(total_stops_raw)

            for segment_option in option.get("OriginDestinationOption", []):
                flight_segment = segment_option.get("FlightSegment", {})
                if flight_segment:
                    try:
                        # Create basic flight segment from DTO
                        dto_segment = DtoFlightSegment(**flight_segment)
                        # Pass the segment_option for additional data
                        domain_segment = self._convert_flight_segment(
                            dto_segment, segment_option
                        )
                        segments.append(domain_segment)
                    except (AttributeError, TypeError, ValueError):
                        # Log warning but continue - we want to get as much data as possible
                        # In production, this would be logged properly
                        continue

            if segments:
                flight_leg = FlightLeg(
                    total_stops=total_stops,
                    flight_segments=segments,
                )
                flight_legs.append(flight_leg)

        # Extract additional info
        requires_passport = fare_data.get("IsPassportMandatory")
        if isinstance(requires_passport, str):
            requires_passport = requires_passport.lower() == "true"
        elif requires_passport is None:
            # None is a valid value from API - default to False
            requires_passport = False

        validating_airline_code = fare_data.get("ValidatingAirlineCode")
        if not validating_airline_code:
            raise ConversionError(
                "Missing ValidatingAirlineCode in fare itinerary",
                source_data=fare_data,
                target_type=FareItinerary,
            )
        validating_airline = self._get_airline_info(validating_airline_code)

        ticket_type = TicketType.E_TICKET
        if fare_data.get("TicketType") == "Paper":
            ticket_type = TicketType.PAPER_TICKET

        return FareItinerary(
            journey_type=journey_type,
            requires_passport=requires_passport,
            sequence_number=str(fare_data.get("SequenceNumber", ""))
            if fare_data.get("SequenceNumber") is not None
            else "",
            ticket_type=ticket_type,
            validating_airline=validating_airline,
            flight_legs=flight_legs,
            pricing=pricing,
        )

    def _convert_passenger_fare_breakdown(
        self, breakdown: dict[str, Any]
    ) -> PassengerFareBreakdown:
        """Convert passenger fare breakdown."""
        # Get passenger type info
        pax_type_quantity = breakdown.get("PassengerTypeQuantity", {})
        passenger_type = PassengerType.ADULT
        if pax_type_quantity.get("Code") == "CHD":
            passenger_type = PassengerType.CHILD
        elif pax_type_quantity.get("Code") == "INF":
            passenger_type = PassengerType.INFANT

        passenger_count_raw = pax_type_quantity.get("Quantity")
        if passenger_count_raw is None:
            raise ConversionError(
                "Missing Quantity in passenger type details",
                source_data=pax_type_quantity,
                target_type=PassengerTypeInfo,
            )

        passenger_type_info = PassengerTypeInfo(
            passenger_type=passenger_type,
            passenger_count=int(passenger_count_raw),
        )

        # Convert passenger fare
        pax_fare = breakdown.get("PassengerFare", {})

        # Convert tax breakdown
        tax_breakdown = []
        for tax in pax_fare.get("Taxes", []):
            tax_code = tax.get("TaxCode")
            tax_amount = tax.get("Amount")
            currency_code = tax.get("CurrencyCode")
            decimal_places = tax.get("DecimalPlaces")

            # Skip tax entries without essential data
            if tax_amount is None:
                logger.warning(f"Skipping tax entry with missing amount: {tax}")
                continue

            # Use a default code if TaxCode is missing
            if not tax_code:
                tax_code = "TAX"  # Generic tax code
                logger.warning(
                    f"Missing TaxCode in tax details, using default 'TAX': {tax}"
                )

            if not currency_code:
                raise ConversionError(
                    "Missing CurrencyCode in tax details",
                    source_data=tax,
                    target_type=TaxDetails,
                )
            if decimal_places is None:
                raise ConversionError(
                    "Missing DecimalPlaces in tax details",
                    source_data=tax,
                    target_type=TaxDetails,
                )

            tax_details = TaxDetails(
                tax_code=tax_code,
                tax_amount=MoneyAmount(
                    amount=Decimal(str(tax_amount)),
                    currency=currency_code,
                    decimal_places=int(decimal_places),
                ),
            )
            tax_breakdown.append(tax_details)

        if not pax_fare.get("BaseFare") or not pax_fare.get("TotalFare"):
            raise ConversionError(
                "Missing required fare amounts in passenger fare",
                source_data=pax_fare,
                target_type=IndividualPassengerFare,
            )

        base_fare = self._convert_money_amount(pax_fare["BaseFare"])
        total_fare = self._convert_money_amount(pax_fare["TotalFare"])

        # Calculate total_tax as total_fare - base_fare
        total_tax_amount = total_fare.amount - base_fare.amount
        total_tax = MoneyAmount(amount=total_tax_amount, currency=total_fare.currency)

        individual_fare = IndividualPassengerFare(
            base_fare=base_fare,
            equivalent_fare=self._convert_money_amount(pax_fare["EquivFare"])
            if pax_fare.get("EquivFare")
            else base_fare,
            service_tax=self._convert_money_amount(pax_fare["ServiceTax"])
            if pax_fare.get("ServiceTax")
            else None,
            surcharges=self._convert_money_amount(pax_fare["Surcharges"])
            if pax_fare.get("Surcharges")
            else None,
            tax_breakdown=tax_breakdown,
            total_tax=total_tax,
            total_fare=total_fare,
        )

        # Convert baggage allowance
        baggage_allowance = []
        for i, baggage in enumerate(breakdown.get("Baggage", [])):
            # Parse baggage string (e.g., "25K", "2P", "SB")
            unit = BaggageUnit.STANDARD
            if baggage.endswith("K") or baggage.endswith("KG"):
                unit = BaggageUnit.KILOGRAM
            elif baggage.endswith("P"):
                unit = BaggageUnit.PIECE

            allowance_info = BaggageAllowanceInfo(
                allowance_type=unit,
                allowance_value=baggage,
                description=f"Baggage allowance: {baggage}",
            )

            baggage_allowance.append(
                BaggageAllowance(
                    segment_number=i,
                    allowance_info=allowance_info,
                    additional_notes=None,
                )
            )

        # Convert cabin baggage allowance
        cabin_baggage_allowance = []
        for i, cabin_baggage in enumerate(breakdown.get("CabinBaggage", [])):
            # Parse cabin baggage string
            unit = BaggageUnit.STANDARD
            if cabin_baggage.endswith("K") or cabin_baggage.endswith("KG"):
                unit = BaggageUnit.KILOGRAM
            elif cabin_baggage.endswith("P"):
                unit = BaggageUnit.PIECE

            allowance_info = BaggageAllowanceInfo(
                allowance_type=unit,
                allowance_value=cabin_baggage,
                description=f"Cabin baggage allowance: {cabin_baggage}",
            )

            cabin_baggage_allowance.append(
                CabinBaggageAllowance(
                    segment_number=i,
                    allowance_info=allowance_info,
                    additional_notes=None,
                )
            )

        # Convert penalty details
        penalty_details = None
        if breakdown.get("PenaltyDetails"):
            penalties = breakdown.get("PenaltyDetails", [])
            if penalties:
                # Handle both list and dict formats
                if isinstance(penalties, list) and len(penalties) > 0:
                    penalty = penalties[0]  # Use first penalty details
                elif isinstance(penalties, dict):
                    penalty = penalties  # Use dict directly
                else:
                    penalty = None

                if penalty:
                    # Validate all required penalty fields
                    refund_allowed = penalty.get("RefundAllowed")
                    refund_amount = penalty.get("RefundPenaltyAmount")
                    refund_currency = penalty.get("Currency")
                    change_allowed = penalty.get("ChangeAllowed")
                    change_amount = penalty.get("ChangePenaltyAmount")
                    change_currency = penalty.get("Currency")

                    if refund_allowed is None:
                        raise ConversionError(
                            "Missing RefundAllowed in penalty details",
                            source_data=penalty,
                            target_type=PenaltyDetails,
                        )
                    if refund_amount is None:
                        raise ConversionError(
                            "Missing RefundPenaltyAmount in penalty details",
                            source_data=penalty,
                            target_type=PenaltyDetails,
                        )
                    if not refund_currency:
                        raise ConversionError(
                            "Missing Currency in penalty details",
                            source_data=penalty,
                            target_type=PenaltyDetails,
                        )
                    if change_allowed is None:
                        raise ConversionError(
                            "Missing ChangeAllowed in penalty details",
                            source_data=penalty,
                            target_type=PenaltyDetails,
                        )
                    if change_amount is None:
                        raise ConversionError(
                            "Missing ChangePenaltyAmount in penalty details",
                            source_data=penalty,
                            target_type=PenaltyDetails,
                        )

                    penalty_details = PenaltyDetails(
                        is_cancellation_allowed=bool(refund_allowed),
                        cancellation_penalty=MoneyAmount(
                            amount=Decimal(str(refund_amount)),
                            currency=refund_currency,
                            decimal_places=2,
                        ),
                        is_change_allowed=bool(change_allowed),
                        change_penalty=MoneyAmount(
                            amount=Decimal(str(change_amount)),
                            currency=change_currency,
                            decimal_places=2,
                        ),
                    )

        # Convert fare basis codes
        fare_basis_codes = []
        for i, code in enumerate(breakdown.get("FareBasisCode", [])):
            fare_basis_codes.append(
                FareBasisCode(
                    code=code,
                    segment_number=i,
                    description=None,
                )
            )

        return PassengerFareBreakdown(
            passenger_type_info=passenger_type_info,
            fare_basis_codes=fare_basis_codes if fare_basis_codes else None,
            individual_passenger_fare=individual_fare,
            baggage_allowance=baggage_allowance,
            cabin_baggage_allowance=cabin_baggage_allowance,
            penalty_details=penalty_details,
        )

    def _convert_validated_fare_itinerary(
        self, fare_data: dict[str, Any]
    ) -> ValidatedFareItinerary:
        """Convert validated fare itinerary from revalidation response."""
        # Extract FareItinerary data if wrapped
        if "FareItinerary" in fare_data:
            fare_data = fare_data["FareItinerary"]

        # For revalidation, AirItineraryFareInfo must be present
        if not fare_data.get("AirItineraryFareInfo"):
            raise ConversionError(
                "Missing AirItineraryFareInfo in validated fare itinerary",
                {"fare_data_keys": list(fare_data.keys())},
            )

        # Ensure OriginDestinationOptions exists
        if not fare_data.get("OriginDestinationOptions"):
            self.logger.warning(
                "Missing OriginDestinationOptions in validated fare itinerary"
            )
            fare_data["OriginDestinationOptions"] = []

        # Similar to _convert_fare_itinerary but with validated fields
        base_itinerary = self._convert_fare_itinerary(fare_data)

        # Extract required booking fields
        required_fields = []
        for field in fare_data.get("RequiredFieldsToBook", []):
            with contextlib.suppress(ValueError):
                required_fields.append(RequiredBookingField(field))

        # Calculate totals from passenger fare breakdown
        # FlightLogic may not update base_fare/total_tax in revalidate, so calculate from breakdown
        calculated_base_fare = Decimal(0)
        calculated_total_tax = Decimal(0)
        currency = base_itinerary.pricing.fare_totals.total_fare.currency

        # Calculate passenger totals for pricing validation (reduced verbosity)
        for breakdown in base_itinerary.pricing.passenger_fare_breakdown:
            base_fare_total = breakdown.individual_passenger_fare.base_fare
            total_fare_total = breakdown.individual_passenger_fare.total_fare
            tax_total = total_fare_total.amount - base_fare_total.amount

            # Sum up totals (individual_passenger_fare is actually TOTAL for all passengers of this type, not per person)
            calculated_base_fare += base_fare_total.amount
            calculated_total_tax += tax_total

        # Log essential fare summary only
        total_calculated = calculated_base_fare + calculated_total_tax
        api_total = base_itinerary.pricing.fare_totals.total_fare.amount
        self.logger.info(
            f"Revalidate fare - API: {api_total} {currency}, Calculated: {total_calculated:.2f} {currency}"
        )

        # Create updated pricing with calculated totals
        calculated_total_fare = calculated_base_fare + calculated_total_tax
        updated_pricing = UpdatedFarePricing(
            has_mixed_booking_classes=base_itinerary.pricing.has_mixed_booking_classes,
            updated_fare_source_code=base_itinerary.pricing.fare_source_code,
            fare_type=base_itinerary.pricing.fare_type,
            is_refundable=base_itinerary.pricing.is_refundable,
            validated_fare_totals=ValidatedFareTotals(
                base_fare=MoneyAmount(amount=calculated_base_fare, currency=currency),
                total_tax=MoneyAmount(amount=calculated_total_tax, currency=currency),
                total_fare=MoneyAmount(amount=calculated_total_fare, currency=currency),
            ),
            passenger_fare_breakdown=base_itinerary.pricing.passenger_fare_breakdown,
        )

        return ValidatedFareItinerary(
            sequence_number=base_itinerary.sequence_number,
            journey_type=base_itinerary.journey_type,
            requires_passport=base_itinerary.requires_passport,
            requires_passport_issue_date=fare_data.get(
                "IsPassportFullDetailsMandatory", None
            ),
            validating_airline=base_itinerary.validating_airline,
            required_booking_fields=required_fields,
            flight_legs=base_itinerary.flight_legs,
            updated_pricing=updated_pricing,
        )

    @staticmethod
    def _parse_service_behavior(behavior: str) -> ServiceBehavior:
        """Parse service behavior string to enum."""
        behavior_map = {
            "PER_PAX": ServiceBehavior.PER_PAX,
            "PER_PAX_OUTBOUND": ServiceBehavior.PER_PAX_OUTBOUND,
            "PER_PAX_INBOUND": ServiceBehavior.PER_PAX_INBOUND,
            "PER_PAX_SEGMENT": ServiceBehavior.PER_PAX_SEGMENT,
            "PER_PAX_SEGMENT_OUTBOUND": ServiceBehavior.PER_PAX_SEGMENT_OUTBOUND,
            "PER_PAX_SEGMENT_INBOUND": ServiceBehavior.PER_PAX_SEGMENT_INBOUND,
            "GROUP_PAX": ServiceBehavior.GROUP_PAX,
            "GROUP_PAX_OUTBOUND": ServiceBehavior.GROUP_PAX_OUTBOUND,
            "GROUP_PAX_INBOUND": ServiceBehavior.GROUP_PAX_INBOUND,
        }
        return behavior_map.get(behavior, ServiceBehavior.PER_PAX)

    @staticmethod
    def _parse_check_in_location(check_in_type: str) -> CheckInLocation:
        """Parse check-in type string to enum."""
        if check_in_type == "ONLINE":
            return CheckInLocation.ONLINE
        if check_in_type == "COUNTER":
            return CheckInLocation.COUNTER
        return CheckInLocation.AIRPORT

    def _convert_service_cost(self, service_cost: Any) -> MoneyAmount:
        """Convert service cost to MoneyAmount."""
        if not service_cost.Amount and service_cost.Amount != 0:
            raise ConversionError(
                "Missing Amount in service cost",
                source_data=service_cost,
                target_type=MoneyAmount,
            )
        if not service_cost.CurrencyCode:
            raise ConversionError(
                "Missing CurrencyCode in service cost",
                source_data=service_cost,
                target_type=MoneyAmount,
            )
        if not service_cost.DecimalPlaces and service_cost.DecimalPlaces != 0:
            raise ConversionError(
                "Missing DecimalPlaces in service cost",
                source_data=service_cost,
                target_type=MoneyAmount,
            )

        return self._convert_money_amount(
            AmountInfo(
                Amount=str(service_cost.Amount),
                CurrencyCode=service_cost.CurrencyCode,
                DecimalPlaces=service_cost.DecimalPlaces,
            )
        )

    def _convert_baggage_service_category(
        self, dynamic_service: DynamicService
    ) -> BaggageServiceCategory:
        """Convert dynamic baggage service to domain schema."""
        service_behavior = self._parse_service_behavior(dynamic_service.Behavior)

        # Convert services
        available_services = []
        for service in dynamic_service.Services:
            check_in_location = self._parse_check_in_location(service.CheckInType)

            service_id = service.ServiceId
            if not service_id:
                raise ConversionError(
                    "Missing ServiceId in baggage service",
                    source_data=service,
                    target_type=BaggageServiceOption,
                )

            description = service.Description
            if not description:
                raise ConversionError(
                    "Missing Description in baggage service",
                    source_data=service,
                    target_type=BaggageServiceOption,
                )

            fare_description = service.FareDescription
            if not fare_description:
                raise ConversionError(
                    "Missing FareDescription in baggage service",
                    source_data=service,
                    target_type=BaggageServiceOption,
                )

            is_mandatory = service.IsMandatory
            if is_mandatory is None:
                raise ConversionError(
                    "Missing IsMandatory in baggage service",
                    source_data=service,
                    target_type=BaggageServiceOption,
                )

            min_qty = service.MinimumQuantity
            if min_qty is None:
                raise ConversionError(
                    "Missing MinimumQuantity in baggage service",
                    source_data=service,
                    target_type=BaggageServiceOption,
                )

            max_qty = service.MaximumQuantity
            if max_qty is None:
                raise ConversionError(
                    "Missing MaximumQuantity in baggage service",
                    source_data=service,
                    target_type=BaggageServiceOption,
                )

            baggage_option = BaggageServiceOption(
                service_id=service_id,
                check_in_location=check_in_location,
                service_description=ServiceDescription(
                    description_text=description,
                    category="baggage",
                ),
                pricing_description=fare_description,
                is_mandatory_service=bool(is_mandatory),
                minimum_quantity=int(min_qty),
                maximum_quantity=int(max_qty),
                service_pricing=self._convert_service_cost(service.ServiceCost),
            )
            available_services.append(baggage_option)

        return BaggageServiceCategory(
            service_behavior=service_behavior,
            allows_multi_select=dynamic_service.IsMultiSelect,
            available_services=available_services,
        )

    def _convert_meal_service_category(
        self, dynamic_service: DynamicService
    ) -> MealServiceCategory:
        """Convert dynamic meal service to domain schema."""
        service_behavior = self._parse_service_behavior(dynamic_service.Behavior)

        # Convert services
        available_services = []
        for service in dynamic_service.Services:
            check_in_location = self._parse_check_in_location(service.CheckInType)

            service_id = service.ServiceId
            if not service_id:
                raise ConversionError(
                    "Missing ServiceId in meal service",
                    source_data=service,
                    target_type=MealServiceOption,
                )

            description = service.Description
            if not description:
                raise ConversionError(
                    "Missing Description in meal service",
                    source_data=service,
                    target_type=MealServiceOption,
                )

            fare_description = service.FareDescription
            if not fare_description:
                raise ConversionError(
                    "Missing FareDescription in meal service",
                    source_data=service,
                    target_type=MealServiceOption,
                )

            is_mandatory = service.IsMandatory
            if is_mandatory is None:
                raise ConversionError(
                    "Missing IsMandatory in meal service",
                    source_data=service,
                    target_type=MealServiceOption,
                )

            min_qty = service.MinimumQuantity
            if min_qty is None:
                raise ConversionError(
                    "Missing MinimumQuantity in meal service",
                    source_data=service,
                    target_type=MealServiceOption,
                )

            max_qty = service.MaximumQuantity
            if max_qty is None:
                raise ConversionError(
                    "Missing MaximumQuantity in meal service",
                    source_data=service,
                    target_type=MealServiceOption,
                )

            meal_option = MealServiceOption(
                service_id=service_id,
                check_in_location=check_in_location,
                service_description=ServiceDescription(
                    description_text=description,
                    category="meal",
                ),
                pricing_description=fare_description,
                is_mandatory_service=bool(is_mandatory),
                minimum_quantity=int(min_qty),
                maximum_quantity=int(max_qty),
                service_pricing=self._convert_service_cost(service.ServiceCost),
            )
            available_services.append(meal_option)

        return MealServiceCategory(
            service_behavior=service_behavior,
            allows_multi_select=dynamic_service.IsMultiSelect,
            available_services=available_services,
        )

    def _convert_baggage_information(
        self, baggage_info: DtoBaggageInfo
    ) -> BaggageInformation:
        """Convert DTO baggage info to domain schema."""
        # Parse baggage code to determine unit
        baggage_code = baggage_info.Baggage
        unit = BaggageUnit.STANDARD
        if baggage_code.endswith("K") or baggage_code.endswith("KG"):
            unit = BaggageUnit.KILOGRAM
        elif baggage_code.endswith("P"):
            unit = BaggageUnit.PIECE
        elif baggage_code == "SB":
            unit = BaggageUnit.STANDARD

        return BaggageInformation(
            flight_number=self._parse_flight_number(baggage_info.FlightNo),
            departure_airport=self._get_airport_info(baggage_info.Departure),
            arrival_airport=self._get_airport_info(baggage_info.Arrival),
            baggage_allowance_code=unit,
        )

    def _convert_fare_rule_details(self, fare_rule: DtoFareRule) -> FareRuleDetails:
        """Convert DTO fare rule to domain schema."""
        # Create route code if city pair is available
        route_code = None
        if fare_rule.CityPair and len(fare_rule.CityPair) >= 6:
            # Assuming city pair format is like "DELBOM" (3+3 characters)
            route_code = RouteCode(
                origin_code=fare_rule.CityPair[:3],
                destination_code=fare_rule.CityPair[3:6],
                formatted_code=fare_rule.CityPair,
            )

        # Try to parse category
        rule_category = None
        if fare_rule.Category:
            with contextlib.suppress(ValueError):
                rule_category = FareRuleCategory(fare_rule.Category)

        return FareRuleDetails(
            airline=self._get_airline_info(fare_rule.Airline),
            route_code=route_code,
            rule_category=rule_category,
            rule_description=fare_rule.Rules,
        )

    @staticmethod
    def _parse_flight_number(flight_no: str) -> FlightNumber:
        """Parse flight number string into components.

        Flight numbers typically follow format: XX123 (airline code + number)
        But can vary, so we handle edge cases.
        """
        if not flight_no:
            raise ConversionError(
                "Empty flight number provided",
                source_data=flight_no,
                target_type=FlightNumber,
            )

        # Try to parse standard format (2-3 letter airline code + numbers)
        import re

        match = re.match(r"^([A-Z]{2,3})(\d+)$", flight_no.upper())
        if match:
            return FlightNumber(
                airline_prefix=match.group(1),
                flight_number=match.group(2),
                formatted_number=flight_no,
            )

        # Fallback: assume first 2 chars are airline code if string is long enough
        if len(flight_no) > 2:
            return FlightNumber(
                airline_prefix=flight_no[:2],
                flight_number=flight_no[2:],
                formatted_number=flight_no,
            )

        # Last resort: treat entire string as flight number with no prefix
        raise ConversionError(
            f"Cannot parse flight number format: {flight_no}",
            source_data=flight_no,
            target_type=FlightNumber,
        )

    def _convert_seat_services(
        self, dynamic_seats: list[dict[str, Any]]
    ) -> list[SeatServiceCategory]:
        """Convert dynamic seat data to seat service categories.

        Seat data structure from FlightLogic is complex with deck/row/seat hierarchy.
        """
        from app.domains.flight.schemas import (
            AircraftDeck,
            SeatOption,
            SeatRow,
            SeatServiceCategory,
        )

        seat_categories = []

        for seat_data in dynamic_seats:
            if not isinstance(seat_data, dict):
                continue

            # Parse deck structure if present
            aircraft_decks = []

            # Check for deck information
            if "Decks" in seat_data:
                for deck_num, deck_data in enumerate(seat_data["Decks"]):
                    if not isinstance(deck_data, dict):
                        continue

                    seat_rows = []

                    # Parse rows in this deck
                    if "Rows" in deck_data:
                        for row_data in deck_data["Rows"]:
                            if not isinstance(row_data, dict):
                                continue

                            row_number = str(row_data.get("RowNumber", ""))
                            available_seats = []

                            # Parse seats in this row
                            if "Seats" in row_data:
                                for seat in row_data["Seats"]:
                                    if isinstance(seat, dict):
                                        is_available = seat.get("IsAvailable")
                                        if is_available is None:
                                            raise ConversionError(
                                                "Missing IsAvailable in seat data",
                                                source_data=seat,
                                                target_type=SeatOption,
                                            )

                                        if bool(is_available):
                                            seat_id = seat.get("SeatId")
                                            if not seat_id:
                                                raise ConversionError(
                                                    "Missing SeatId in available seat",
                                                    source_data=seat,
                                                    target_type=SeatOption,
                                                )

                                            # Extract airline info from seat data if available
                                            airline_code = seat.get("AirlineCode", "")
                                            flight_num = seat.get("FlightNumber", "")

                                            seat_option = SeatOption(
                                                service_id=seat_id,
                                                airline=self._get_airline_info(
                                                    airline_code
                                                )
                                                if airline_code
                                                else None,
                                                flight_number=self._parse_flight_number(
                                                    flight_num
                                                )
                                                if flight_num
                                                else None,
                                            )
                                            available_seats.append(seat_option)

                            if available_seats:
                                seat_row = SeatRow(
                                    row_number=row_number,
                                    available_seats=available_seats,
                                )
                                seat_rows.append(seat_row)

                    if seat_rows:
                        aircraft_deck = AircraftDeck(
                            deck_number=deck_num,
                            seat_rows=seat_rows,
                        )
                        aircraft_decks.append(aircraft_deck)

            # Fallback: Try to parse a simpler structure
            elif "SeatMap" in seat_data:
                # Handle alternative seat map structure
                seat_map = seat_data["SeatMap"]
                if isinstance(seat_map, list):
                    # Create a single deck with all seats
                    seat_rows = []
                    current_row = None
                    current_row_seats = []

                    for seat_info in seat_map:
                        if isinstance(seat_info, dict):
                            row_num = seat_info.get("Row", "")

                            if row_num != current_row:
                                # Save previous row if it has seats
                                if current_row and current_row_seats:
                                    seat_row = SeatRow(
                                        row_number=str(current_row),
                                        available_seats=current_row_seats,
                                    )
                                    seat_rows.append(seat_row)

                                # Start new row
                                current_row = row_num
                                current_row_seats = []

                            # Add seat to current row if available
                            is_available = seat_info.get("IsAvailable")
                            if is_available is None:
                                raise ConversionError(
                                    "Missing IsAvailable in seat info",
                                    source_data=seat_info,
                                    target_type=SeatOption,
                                )

                            if bool(is_available):
                                seat_id = seat_info.get("SeatId")
                                if not seat_id:
                                    raise ConversionError(
                                        "Missing SeatId in available seat",
                                        source_data=seat_info,
                                        target_type=SeatOption,
                                    )

                                seat_option = SeatOption(
                                    service_id=seat_id,
                                    airline=None,  # Will be populated if data available
                                    flight_number=None,  # Will be populated if data available
                                )
                                current_row_seats.append(seat_option)

                    # Add last row
                    if current_row and current_row_seats:
                        seat_row = SeatRow(
                            row_number=str(current_row),
                            available_seats=current_row_seats,
                        )
                        seat_rows.append(seat_row)

                    if seat_rows:
                        aircraft_deck = AircraftDeck(
                            deck_number=0,
                            seat_rows=seat_rows,
                        )
                        aircraft_decks.append(aircraft_deck)

            if aircraft_decks:
                seat_category = SeatServiceCategory(
                    aircraft_decks=aircraft_decks,
                )
                seat_categories.append(seat_category)

        return seat_categories

    # ============================================================
    # TRIP DETAILS PARSING METHODS
    # ============================================================

    def _parse_trip_details_response(
        self, dto: FlightLogicTripDetailsResponse
    ) -> TripDetailsResponse:
        """Convert FlightLogic trip details response to internal schema.

        This function handles multiple possible response formats from FlightLogic API.
        """
        # Find the booking data in various possible locations
        booking_data = self._extract_booking_data(dto)

        if not booking_data:
            logger.error("No booking data found in FlightLogic response")
            raise ValueError("Invalid trip details response from FlightLogic")

        # Parse all the required fields
        external_booking_reference = self._extract_external_booking_reference(
            booking_data
        )
        booking_status = FlightLogicSchemaAdapter._parse_booking_status(booking_data)
        ticket_status = self._parse_ticket_status(booking_data)
        origin, destination = self._parse_airports(booking_data)
        fare_type = self._parse_fare_type(booking_data)
        passengers = self._parse_passengers(booking_data)
        segments = self._parse_flight_segments(booking_data, len(passengers))
        pricing, fare_breakdown = self._parse_pricing(booking_data, len(passengers))
        extra_services = self._parse_extra_services(booking_data)
        booking_notes = self._parse_booking_notes(booking_data)

        # Determine environment from response
        environment = FlightAPIEnvironment.TEST
        if (
            booking_data.get("Environment") == "Production"
            or booking_data.get("Target") == "Production"
        ):
            environment = FlightAPIEnvironment.PRODUCTION

        # Calculate cross_border_indicator based on country codes
        # FlightLogic's CrossBorderIndicator is unreliable, so we calculate it ourselves
        cross_border = False
        if origin.country_code and destination.country_code:
            cross_border = origin.country_code != destination.country_code
        else:
            # Fallback to FlightLogic value if country codes not available
            cross_border = booking_data.get("CrossBorderIndicator", False)

        # Build the response
        return TripDetailsResponse(
            success=True,
            booking_status=booking_status,
            cross_border_indicator=cross_border,
            destination=destination,
            origin=origin,
            fare_type=fare_type,
            is_commissionable=booking_data.get("IsCommissionable", False),
            is_mo_fare=booking_data.get("IsMOFare", False),
            external_booking_reference=external_booking_reference,
            ticket_status=ticket_status,
            environment=environment,
            passengers=passengers,
            segments=segments,
            pricing=pricing,
            fare_breakdown=fare_breakdown,
            extra_services=extra_services,
            booking_notes=booking_notes,
            errors=[],
        )

    def _merge_trip_details_inbound_segments(
        self,
        booking_data: dict[str, Any],
        *,
        trip_response: dict[str, Any] | None = None,
        dto: FlightLogicTripDetailsResponse | None = None,
    ) -> None:
        """Append Indian domestic RT inbound segments (TripDetailsResultInbound) to FlightSegments."""
        inbound: dict[str, Any] | None = None
        if trip_response is not None:
            raw = trip_response.get("TripDetailsResultInbound")
            inbound = raw if isinstance(raw, dict) else None
        elif dto is not None:
            raw = dto.model_dump().get("TripDetailsResultInbound")
            inbound = raw if isinstance(raw, dict) else None
        if not inbound:
            return

        extra: list[dict[str, Any]] = []
        travel_itinerary = inbound.get("TravelItinerary")
        if isinstance(travel_itinerary, dict):
            itinerary_info = travel_itinerary.get("ItineraryInfo")
            if isinstance(itinerary_info, dict) and itinerary_info.get(
                "ReservationItems"
            ):
                for item in itinerary_info["ReservationItems"]:
                    if isinstance(item, dict):
                        extra.append(item.get("ReservationItem", item))
        if not extra:
            for key in ("FlightSegments", "Segments"):
                segs = inbound.get(key)
                if isinstance(segs, list):
                    extra.extend(s for s in segs if isinstance(s, dict))
                    break
        if not extra:
            return

        existing = booking_data.get("FlightSegments")
        if existing is None:
            existing = booking_data.get("Segments") or []
        if not isinstance(existing, list):
            existing = [existing]
        booking_data["FlightSegments"] = list(existing) + extra

    def _extract_booking_data(
        self, dto: FlightLogicTripDetailsResponse
    ) -> dict[str, Any]:
        """Extract booking data from various possible response structures."""
        # First, check for the actual FlightLogic response structure
        # The real structure is: TripDetailsResponse -> TripDetailsResult -> TravelItinerary
        dto_dict = dto.model_dump(exclude_none=True)

        # Try to extract TravelItinerary from nested structure
        if "TripDetailsResponse" in dto_dict:
            trip_response = dto_dict["TripDetailsResponse"]
            if "TripDetailsResult" in trip_response:
                trip_result = trip_response["TripDetailsResult"]
                if "TravelItinerary" in trip_result:
                    travel_itinerary = trip_result["TravelItinerary"]

                    # Merge ItineraryInfo data into TravelItinerary if it exists
                    # The actual data is nested in ItineraryInfo:
                    # - CustomerInfos (passengers) - each wrapped in "CustomerInfo"
                    # - ReservationItems (segments) - each wrapped in "ReservationItem"
                    # - ItineraryPricing (pricing)
                    if "ItineraryInfo" in travel_itinerary:
                        itinerary_info = travel_itinerary["ItineraryInfo"]

                        # Flatten nested data to where parsing methods expect it
                        # Unwrap CustomerInfos: [{"CustomerInfo": {...}}] -> [{...}]
                        if "CustomerInfos" in itinerary_info:
                            customer_infos = itinerary_info["CustomerInfos"]
                            travel_itinerary["Passengers"] = [
                                item.get("CustomerInfo", item)
                                for item in customer_infos
                            ]

                        # Unwrap ReservationItems: [{"ReservationItem": {...}}] -> [{...}]
                        if "ReservationItems" in itinerary_info:
                            reservation_items = itinerary_info["ReservationItems"]
                            logger.debug(
                                f"Found {len(reservation_items)} ReservationItems in response"
                            )
                            travel_itinerary["FlightSegments"] = [
                                item.get("ReservationItem", item)
                                for item in reservation_items
                            ]
                        else:
                            logger.warning("No ReservationItems found in ItineraryInfo")

                        if "ItineraryPricing" in itinerary_info:
                            travel_itinerary["FareDetails"] = itinerary_info[
                                "ItineraryPricing"
                            ]

                        # Map TripDetailsPTC_FareBreakdowns to FareBreakdown
                        if "TripDetailsPTC_FareBreakdowns" in itinerary_info:
                            # Unwrap the nested structure: [{"TripDetailsPTC_FareBreakdown": {...}}] -> [{...}]
                            fare_breakdowns = itinerary_info[
                                "TripDetailsPTC_FareBreakdowns"
                            ]
                            if isinstance(fare_breakdowns, list):
                                travel_itinerary["FareBreakdown"] = [
                                    item.get("TripDetailsPTC_FareBreakdown", item)
                                    for item in fare_breakdowns
                                ]
                            else:
                                travel_itinerary["FareBreakdown"] = [fare_breakdowns]

                    self._merge_trip_details_inbound_segments(
                        travel_itinerary, trip_response=trip_response
                    )
                    return travel_itinerary

        # Fallback: Try different possible locations for booking data
        if isinstance(dto.TripDetailsResult, TripDetailsBooking):
            data = dto.TripDetailsResult.model_dump()
            self._merge_trip_details_inbound_segments(data, dto=dto)
            return data
        if isinstance(dto.TripDetailsResult, dict):
            data = dict(dto.TripDetailsResult)
            self._merge_trip_details_inbound_segments(data, dto=dto)
            return data
        if dto.BookingDetails:
            if isinstance(dto.BookingDetails, TripDetailsBooking):
                return dto.BookingDetails.model_dump()
            return dto.BookingDetails
        if dto.TripDetails:
            if isinstance(dto.TripDetails, TripDetailsBooking):
                return dto.TripDetails.model_dump()
            return dto.TripDetails
        if dto.GetBookingDetailsResponse:
            return dto.GetBookingDetailsResponse

        # If none of the above, try the raw dto
        return dto_dict

    def _extract_external_booking_reference(self, data: dict[str, Any]) -> str:
        """
        Extract FlightLogic booking reference (UniqueID).

        Note: This returns FlightLogic's internal booking ID, NOT airline PNR.
        PNR should be extracted separately using _extract_airline_pnr().
        """
        return data.get("UniqueID") or data.get("external_booking_reference")

    def _extract_airline_pnr(
        self,
        seg: dict[str, Any] | None,
        data: dict[str, Any],
        marketing_airline: AirlineInfo | None = None,
    ) -> AirlinePNR | None:
        """
        Extract airline PNR from FlightLogic response.

        FlightLogic can return PNR in multiple places:
        - seg.AirlinePNR (per segment) - preferred
        - data.PNR (top-level, single PNR for whole booking)

        Args:
            seg: Segment data (if available)
            data: Top-level response data
            marketing_airline: Marketing airline info (if available)

        Returns:
            AirlinePNR object or None if PNR not found
        """
        # Try to get PNR code from segment first, then fall back to top-level
        pnr_code = None
        if seg:
            pnr_code = seg.get("AirlinePNR")
        if not pnr_code:
            pnr_code = data.get("PNR")

        if not pnr_code:
            return None

        # Use provided marketing_airline or try to extract from segment
        from app.domains.airline import get_airline_name

        airline = marketing_airline
        if not airline and seg:
            # Try to extract airline from segment
            airline_data = seg.get("MarketingAirline") or seg.get("OperatingAirline")
            if airline_data:
                airline_code = airline_data.get("Code", "")
                airline_name = airline_data.get("Name", "") or get_airline_name(
                    airline_code
                )
                airline = AirlineInfo(iata_code=airline_code, airline_name=airline_name)

        # If still no airline, use a default placeholder
        if not airline:
            airline = AirlineInfo(iata_code="", airline_name="Unknown Airline")

        # Parse PNR status if available
        pnr_status = None
        status_raw = data.get("PNRStatus")
        if status_raw:
            try:
                pnr_status = PNRStatus(status_raw)
            except (ValueError, TypeError):
                pnr_status = None

        return AirlinePNR(pnr_code=pnr_code, airline=airline, status=pnr_status)

    def _parse_ticket_status(self, data: dict[str, Any]) -> TicketStatus:
        """Parse ticket status from response."""
        ticket_raw = data.get("TicketStatus", "not_issued")

        if isinstance(ticket_raw, str):
            return parse_ticket_status_from_flightlogic_string(ticket_raw)

        return TicketStatus.NOT_ISSUED

    def _parse_fare_type(self, data: dict[str, Any]) -> FareType:
        """Parse fare type from response."""
        fare_type_raw = data.get("FareType", "Public")

        if isinstance(fare_type_raw, str):
            fare_lower = fare_type_raw.lower()
            if "private" in fare_lower:
                return FareType.PRIVATE
            if "web" in fare_lower:
                return FareType.WEB_FARE

        return FareType.PUBLIC

    async def _parse_airports_with_country(
        self, data: dict[str, Any]
    ) -> tuple[AirportInfo, AirportInfo]:
        """Parse origin and destination airports with country codes.

        Uses either mwgg/Airports (default) or FlightLogic API based on
        VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS environment variable.
        """
        from app.core.config import settings

        # Try to get airport info from various fields
        origin_code = data.get("Origin", data.get("DepartureAirport", ""))
        dest_code = data.get("Destination", data.get("ArrivalAirport", ""))

        # Helper to build AirportInfo with country code lookup
        async def build_airport_info(code: Any) -> AirportInfo:
            if isinstance(code, str) and code:
                # Look up detailed airport info including country code
                if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
                    # Use FlightLogic API via FlightService
                    logger.debug(
                        f"Using FlightLogic API for airport parsing in FlightLogic adapter: '{code}'"
                    )
                    from app.domains.flight.service import FlightService

                    flight_service = FlightService(current_user=None)
                    airport_data = await flight_service.get_airport_info(code)
                    if airport_data:
                        return AirportInfo(
                            iata_code=code,
                            airport_name=airport_data.get("airport_name")
                            or airport_data.get("name", f"{code} Airport"),
                            city_name=airport_data.get("city", code),
                            country_code=airport_data.get("country"),
                        )
                # Use mwgg/Airports (default)
                logger.debug(
                    f"Using mwgg/Airports for airport parsing in FlightLogic adapter: '{code}'"
                )
                from app.domains.airport.airport_resolver import airport_resolver

                airport_data = await airport_resolver.get_airport_info(code)
                if airport_data:
                    return AirportInfo(
                        iata_code=code,
                        airport_name=airport_data.get("name", f"{code} Airport"),
                        city_name=airport_data.get("city", code),
                        country_code=airport_data.get("country"),
                    )
                return AirportInfo(
                    iata_code=code, airport_name=f"{code} Airport", city_name=code
                )
            if isinstance(code, dict):
                return AirportInfo(
                    iata_code=code.get("Code", code.get("code", "UNK")),
                    airport_name=code.get("Name", code.get("name", "Unknown Airport")),
                    city_name=code.get("City", code.get("city", "Unknown")),
                )
            return AirportInfo(
                iata_code="UNK", airport_name="Unknown Airport", city_name="Unknown"
            )

        origin = await build_airport_info(origin_code)
        destination = await build_airport_info(dest_code)

        return origin, destination

    def _parse_airports(self, data: dict[str, Any]) -> tuple[AirportInfo, AirportInfo]:
        """Parse origin and destination airports (sync version without country codes)."""
        # Try to get airport info from various fields
        origin_code = data.get("Origin", data.get("DepartureAirport", ""))
        dest_code = data.get("Destination", data.get("ArrivalAirport", ""))

        # If codes are strings, create basic airport info
        if isinstance(origin_code, str) and origin_code:
            origin = AirportInfo(
                iata_code=origin_code,
                airport_name=f"{origin_code} Airport",
                city_name=origin_code,
            )
        elif isinstance(origin_code, dict):
            origin = AirportInfo(
                iata_code=origin_code.get("Code", origin_code.get("code", "UNK")),
                airport_name=origin_code.get(
                    "Name", origin_code.get("name", "Unknown Airport")
                ),
                city_name=origin_code.get("City", origin_code.get("city", "Unknown")),
            )
        else:
            origin = AirportInfo(
                iata_code="UNK", airport_name="Unknown Airport", city_name="Unknown"
            )

        if isinstance(dest_code, str) and dest_code:
            destination = AirportInfo(
                iata_code=dest_code,
                airport_name=f"{dest_code} Airport",
                city_name=dest_code,
            )
        elif isinstance(dest_code, dict):
            destination = AirportInfo(
                iata_code=dest_code.get("Code", dest_code.get("code", "UNK")),
                airport_name=dest_code.get(
                    "Name", dest_code.get("name", "Unknown Airport")
                ),
                city_name=dest_code.get("City", dest_code.get("city", "Unknown")),
            )
        else:
            destination = AirportInfo(
                iata_code="UNK", airport_name="Unknown Airport", city_name="Unknown"
            )

        return origin, destination

    def _parse_passengers(self, data: dict[str, Any]) -> list[PassengerDetails]:
        """Parse passenger details from response."""
        passengers = []

        # Get passenger data from various possible fields
        pax_data = data.get("Passengers", data.get("PassengerDetails", []))

        if not pax_data and "TravelItinerary" in data:
            # Try getting from TravelItinerary structure
            pax_data = data.get("TravelItinerary", {}).get("PassengerInfo", [])

        if not isinstance(pax_data, list):
            pax_data = [pax_data]

        for idx, pax in enumerate(pax_data):
            if not isinstance(pax, dict):
                continue

            # Parse passenger type
            pax_type_raw = pax.get("PassengerType", pax.get("Type", "ADT"))
            passenger_type = PassengerType.ADULT
            if pax_type_raw == "CHD":
                passenger_type = PassengerType.CHILD
            elif pax_type_raw == "INF":
                passenger_type = PassengerType.INFANT

            # Parse personal info - FlightLogic uses "Passenger" prefix
            first_name = pax.get("PassengerFirstName") or pax.get("FirstName")
            last_name = pax.get("PassengerLastName") or pax.get("LastName")
            title = pax.get("PassengerTitle") or pax.get("Title")

            if not first_name or not last_name:
                continue  # Skip passengers without required name data

            person_name = PersonName(
                title=title,
                first_name=first_name,
                last_name=last_name,
                full_name=f"{first_name} {last_name}",
            )

            personal_info = PersonalInfo(
                name=person_name,
                date_of_birth=pax.get("DateOfBirth"),
                nationality=pax.get("PassengerNationality") or pax.get("Nationality"),
            )

            # Parse travel documents if available
            travel_docs = None
            if pax.get("PassportNumber"):
                travel_docs = TravelDocuments(
                    passport_number=pax.get("PassportNumber"),
                    passport_expiry_date=pax.get("PassportExpiryDate"),
                    passport_issue_country=pax.get("PassportIssuingCountry"),
                    passport_issue_date=pax.get("PassportIssueDate"),
                )

            # Parse contact info - FlightLogic field names
            email = (
                pax.get("EmailAddress") or pax.get("Email") or data.get("CustomerEmail")
            )
            phone = (
                pax.get("PhoneNumber") or pax.get("Phone") or data.get("CustomerPhone")
            )

            # Only create contact_info if we have at least email or phone
            contact_info = None
            if email or phone:
                contact_info = ContactInformation(
                    email=email,
                    phone=phone,
                    area_code=data.get("AreaCode"),
                    country_code=data.get("CountryCode"),
                )

            # Only create postal code if we have the data
            postal_code = None
            postal_code_value = data.get("PostCode")
            country_code_value = data.get("CountryCode")
            if postal_code_value and country_code_value:
                postal_code = PostalCode(
                    code=postal_code_value, country=country_code_value
                )

            passengers.append(
                PassengerDetails(
                    passenger_type=passenger_type,
                    personal_info=personal_info,
                    reference_id=idx + 1,
                    e_ticket_number=pax.get("eTicketNumber")
                    or pax.get(
                        "TicketNumber"
                    ),  # FlightLogic uses "eTicketNumber", fallback for backwards compat
                    travel_documents=travel_docs,
                    contact_info=contact_info,
                    postal_code=postal_code,
                )
            )

        return passengers

    def _parse_flight_segments(
        self, data: dict[str, Any], passenger_count: int = 1
    ) -> list[TripDetailsFlightSegment]:
        """Parse flight segments from response."""
        segments = []

        # Get segments from various possible fields
        segments_data = (
            data.get("FlightSegments")
            or data.get("Segments")
            or data.get("OriginDestinationOptions", [])
        )

        if not isinstance(segments_data, list):
            segments_data = [segments_data]

        for idx, seg in enumerate(segments_data):
            if not isinstance(seg, dict):
                continue

            # Parse datetime strings
            dep_dt = self._parse_datetime(seg.get("DepartureDateTime", ""))
            arr_dt = self._parse_datetime(seg.get("ArrivalDateTime", ""))

            # Parse airports - handle both field names
            dep_code = seg.get("DepartureAirportCode") or seg.get(
                "DepartureAirportLocationCode"
            )
            arr_code = seg.get("ArrivalAirportCode") or seg.get(
                "ArrivalAirportLocationCode"
            )

            if not dep_code or not arr_code:
                self.logger.warning(
                    f"Missing airport codes in segment - skipping: dep={dep_code}, arr={arr_code}"
                )
                continue

            dep_airport = AirportInfo(
                iata_code=dep_code,
                airport_name=seg.get("DepartureAirportName"),
                city_name=seg.get("DepartureCity"),
            )

            arr_airport = AirportInfo(
                iata_code=arr_code,
                airport_name=seg.get("ArrivalAirportName"),
                city_name=seg.get("ArrivalCity"),
            )

            # Parse airlines with name resolution fallback
            from app.domains.airline import get_airline_name

            marketing_code = seg.get("MarketingAirlineCode")
            operating_code = seg.get("OperatingAirlineCode") or marketing_code

            if not marketing_code:
                self.logger.warning(
                    "Missing marketing airline code in segment - skipping"
                )
                continue

            # Try to get airline name from FlightLogic response, fallback to resolver
            marketing_name = seg.get("MarketingAirlineName") or get_airline_name(
                marketing_code
            )
            operating_name = (
                seg.get("OperatingAirlineName")
                or seg.get("MarketingAirlineName")
                or get_airline_name(operating_code)
            )

            marketing_airline = AirlineInfo(
                iata_code=marketing_code, icao_code=None, airline_name=marketing_name
            )

            operating_airline = AirlineInfo(
                iata_code=operating_code, icao_code=None, airline_name=operating_name
            )

            # Parse flight numbers
            flight_num = seg.get("FlightNumber")
            op_flight_num = seg.get("OperatingFlightNumber") or flight_num

            if not flight_num:
                self.logger.warning("Missing flight number in segment - skipping")
                continue

            marketing_flight = FlightNumber(
                airline_prefix=marketing_code,
                flight_number=flight_num,
                formatted_number=f"{marketing_code}{flight_num}",
            )

            operating_flight = FlightNumber(
                airline_prefix=operating_code,
                flight_number=op_flight_num,
                formatted_number=f"{operating_code}{op_flight_num}",
            )

            # Parse aircraft - FlightLogic uses AirEquipmentType in trip details
            aircraft_code = (
                seg.get("AirEquipmentType")
                or seg.get("AircraftType")
                or seg.get("Equipment")
            )

            # Make aircraft info optional - use "Unknown" if not provided
            aircraft = None
            if aircraft_code:
                aircraft = AircraftInfo(
                    aircraft_type_code=aircraft_code,
                    manufacturer=seg.get("AircraftManufacturer"),
                    model_name=seg.get("AircraftName"),
                )

            # Parse duration
            duration_minutes = seg.get("Duration", seg.get("JourneyDuration", 0))
            duration = Duration(
                total_minutes=duration_minutes if duration_minutes else 0
            )

            # Parse cabin class
            cabin_raw = seg.get("CabinClass", seg.get("CabinClassCode", "Y"))
            cabin_class = CabinClass.ECONOMY
            if cabin_raw in ["C", "J", "BUSINESS"]:
                cabin_class = CabinClass.BUSINESS
            elif cabin_raw in ["F", "FIRST"]:
                cabin_class = CabinClass.FIRST
            elif cabin_raw in ["S", "PREMIUM"]:
                cabin_class = CabinClass.PREMIUM_ECONOMY

            # Extract airline PNR using centralized method
            airline_pnr = self._extract_airline_pnr(seg, data, marketing_airline)
            if not airline_pnr:
                # PNR is required for TripDetailsFlightSegment - create placeholder
                airline_pnr = AirlinePNR(
                    pnr_code="PENDING", airline=marketing_airline, status=None
                )

            segments.append(
                TripDetailsFlightSegment(
                    segment_id=idx + 1,
                    departure_datetime=dep_dt,
                    arrival_datetime=arr_dt,
                    departure_airport=dep_airport,
                    arrival_airport=arr_airport,
                    departure_terminal=TerminalInfo(
                        terminal_name=seg.get("DepartureTerminal"), airport=dep_airport
                    )
                    if seg.get("DepartureTerminal")
                    else None,
                    arrival_terminal=TerminalInfo(
                        terminal_name=seg.get("ArrivalTerminal"), airport=arr_airport
                    )
                    if seg.get("ArrivalTerminal")
                    else None,
                    marketing_flight_number=marketing_flight,
                    operating_airline=operating_airline,
                    marketing_airline=marketing_airline,
                    operating_flight_number=operating_flight,
                    aircraft=aircraft,
                    flight_duration=duration,
                    segment_stops=seg.get("StopQuantity", 0),
                    passenger_count=passenger_count,
                    airline_pnr=airline_pnr,
                    cabin_class=cabin_class,
                    booking_class_code=BookingClassCode(
                        class_code=seg.get("BookingClass")
                    )
                    if seg.get("BookingClass")
                    else None,
                    e_ticket=bool(seg.get("Eticket") or seg.get("ETicket")),
                )
            )

        return segments

    def _parse_datetime(self, dt_str: str) -> DateTime:
        """Parse datetime string to DateTime object.

        Raises ConversionError if datetime string is missing or invalid.
        Keeps datetime as naive (local airport time) - no timezone conversion.
        """
        if not dt_str:
            raise ConversionError("Missing datetime string", {"dt_str": dt_str})

        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            # Remove timezone info to keep as naive datetime (local airport time)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return DateTime(value=dt)
        except Exception as e1:
            # Try parsing as-is with datetime
            try:
                from dateutil import parser

                dt = parser.parse(dt_str)
                # Remove timezone info to keep as naive datetime (local airport time)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                return DateTime(value=dt)
            except Exception as e2:
                raise ConversionError(
                    f"Invalid datetime format: {dt_str}",
                    {"dt_str": dt_str, "iso_error": str(e1), "parser_error": str(e2)},
                ) from e2

    def _extract_currency_from_data(
        self, data: dict[str, Any], fare_data: dict[str, Any] | None = None
    ) -> str | None:
        """Extract currency code from nested FlightLogic response structures."""
        if fare_data is None:
            fare_data = (
                data.get("FareDetails")
                or data.get("TotalFare")
                or data.get("ItineraryPricing")
                or {}
            )

        return (
            data.get("Currency")
            or fare_data.get("CurrencyCode")
            or (
                fare_data.get("TotalFare", {}).get("CurrencyCode")
                if isinstance(fare_data.get("TotalFare"), dict)
                else None
            )
            or (
                fare_data.get("EquiFare", {}).get("CurrencyCode")
                if isinstance(fare_data.get("EquiFare"), dict)
                else None
            )
            or (
                fare_data.get("Tax", {}).get("CurrencyCode")
                if isinstance(fare_data.get("Tax"), dict)
                else None
            )
        )

    def _parse_pricing(
        self, data: dict[str, Any], passenger_count: int
    ) -> tuple[FarePricing, list[FareBreakdown]]:
        """Parse pricing information from response."""
        # Get fare details from various possible locations
        fare_data = (
            data.get("FareDetails")
            or data.get("TotalFare")
            or data.get("ItineraryPricing")
            or {}
        )

        # Extract currency using helper method
        currency = self._extract_currency_from_data(data, fare_data)
        if not currency:
            # Log detailed information about missing currency
            self.logger.error(
                f"Missing currency in trip details. "
                f"Top-level keys: {list(data.keys())}, "
                f"Fare data keys: {list(fare_data.keys()) if isinstance(fare_data, dict) else 'N/A'}, "
                f"Fare data sample: {str(fare_data)[:200]}"
            )
            raise ValueError("Missing required currency in trip details response")

        # Create money amounts - FlightLogic uses EquiFare instead of BaseFare
        base_amount = self._parse_money_amount(
            fare_data.get("BaseFare") or fare_data.get("EquiFare"), currency
        )
        tax_amount = self._parse_money_amount(fare_data.get("Tax"), currency)
        total_amount = self._parse_money_amount(
            fare_data.get("TotalFare") or data.get("TotalAmount"), currency
        )

        # If total is not available, calculate it
        if total_amount.amount == 0:
            total_amount = MoneyAmount(
                amount=base_amount.amount + tax_amount.amount,
                currency=currency,
                decimal_places=2,
            )

        # Create fare totals
        fare_totals = FareTotals(
            base_fare=base_amount,
            equivalent_fare=base_amount,
            service_tax=MoneyAmount(amount=0, currency=currency, decimal_places=2),
            total_tax=tax_amount,
            total_fare=total_amount,
        )

        # Create pricing
        fare_source_code = self._extract_external_booking_reference(data)
        if not fare_source_code:
            self.logger.error("Missing fare source code in trip details")
            raise ValueError(
                "Missing required booking reference in trip details response"
            )

        pricing = FarePricing(
            has_mixed_booking_classes=False,
            fare_source_code=fare_source_code,
            fare_type=self._parse_fare_type(data),
            is_refundable=fare_data.get("IsRefundable", False)
            if isinstance(fare_data.get("IsRefundable"), bool)
            else False,
            fare_totals=fare_totals,
            passenger_fare_breakdown=[],  # Will be filled below
        )

        # Create fare breakdown per passenger
        fare_breakdown = []

        # Get breakdown data from various possible locations
        breakdown_data = (
            fare_data.get("FareBreakdown") or data.get("FareBreakdown") or []
        )
        if not isinstance(breakdown_data, list):
            breakdown_data = [breakdown_data] if breakdown_data else []

        if not breakdown_data:
            self.logger.warning("Missing fare breakdown data in trip details")
            # For trip details, fare breakdown may not be critical - create basic breakdown
            fare_breakdown = [
                FareBreakdown(
                    passenger_type_info=PassengerTypeInfo(
                        passenger_type=PassengerType.ADULT,
                        passenger_count=passenger_count,
                    ),
                    individual_fare=IndividualPassengerFare(
                        base_fare=base_amount,
                        equivalent_fare=base_amount,
                        service_tax=MoneyAmount(
                            amount=0, currency=currency, decimal_places=2
                        ),
                        tax_breakdown=[],
                        total_tax=MoneyAmount(
                            amount=total_amount.amount - base_amount.amount,
                            currency=currency,
                            decimal_places=2,
                        ),
                        total_fare=total_amount,
                    ),
                    # Optional fields with default_factory=list are automatically set to empty lists
                )
            ]
        else:
            # Process breakdown data
            for breakdown in breakdown_data:
                if isinstance(breakdown, dict):
                    pax_quantity = breakdown.get("PassengerTypeQuantity", {})
                    pax_type_code = pax_quantity.get("Code", "ADT")
                    pax_count = pax_quantity.get("Quantity", 1)

                    # Map passenger type code to enum
                    pax_type = PassengerType.ADULT
                    if pax_type_code == "CHD":
                        pax_type = PassengerType.CHILD
                    elif pax_type_code == "INF":
                        pax_type = PassengerType.INFANT

                    # Get passenger fare from breakdown
                    pax_fare = breakdown.get("TripDetailsPassengerFare", {})

                    # Parse fare amounts for this passenger type
                    pax_base = self._parse_money_amount(
                        pax_fare.get("BaseFare") or pax_fare.get("EquiFare"), currency
                    )
                    pax_service_tax = self._parse_money_amount(
                        pax_fare.get("ServiceTax"), currency
                    )
                    # pax_tax is available but not used in fare breakdown schema
                    # keeping the parse line commented for reference if needed later
                    # pax_tax = self._parse_money_amount(pax_fare.get("Tax"), currency)
                    pax_total = self._parse_money_amount(
                        pax_fare.get("TotalFare"), currency
                    )

                    fare_breakdown.append(
                        FareBreakdown(
                            passenger_type_info=PassengerTypeInfo(
                                passenger_type=pax_type, passenger_count=pax_count
                            ),
                            individual_fare=IndividualPassengerFare(
                                base_fare=pax_base,
                                equivalent_fare=pax_base,
                                service_tax=pax_service_tax,
                                tax_breakdown=[],
                                total_tax=MoneyAmount(
                                    amount=pax_total.amount - pax_base.amount,
                                    currency=currency,
                                    decimal_places=2,
                                ),
                                total_fare=pax_total,
                            ),
                            # Optional fields with default_factory=list are automatically set to empty lists
                        )
                    )

        # Update pricing with fare breakdown
        pricing.passenger_fare_breakdown = fare_breakdown

        return pricing, fare_breakdown

    def _parse_money_amount(
        self, amount_data: Any, default_currency: str | None = None
    ) -> MoneyAmount:
        """Parse money amount from various formats.

        Raises ConversionError if amount data is invalid or currency is missing.
        """
        # Handle None/missing amounts - return zero
        if amount_data is None:
            if not default_currency:
                raise ConversionError(
                    "Currency required for missing amount", {"amount_data": amount_data}
                )
            return MoneyAmount(amount=0, currency=default_currency, decimal_places=2)

        if isinstance(amount_data, dict):
            currency = amount_data.get("CurrencyCode") or default_currency
            if not currency:
                raise ConversionError(
                    "Missing currency code in money amount",
                    {"amount_data": amount_data, "default_currency": default_currency},
                )

            return MoneyAmount(
                amount=float(amount_data.get("Amount", 0)),
                currency=currency,
                decimal_places=amount_data.get("DecimalPlaces", 2),
            )
        if isinstance(amount_data, (int, float)):
            if not default_currency:
                raise ConversionError(
                    "Currency required for numeric amount", {"amount": amount_data}
                )
            return MoneyAmount(
                amount=float(amount_data), currency=default_currency, decimal_places=2
            )
        if isinstance(amount_data, str):
            if not default_currency:
                raise ConversionError(
                    "Currency required for string amount", {"amount": amount_data}
                )
            try:
                return MoneyAmount(
                    amount=float(amount_data),
                    currency=default_currency,
                    decimal_places=2,
                )
            except ValueError as e:
                raise ConversionError(
                    f"Invalid amount format: {amount_data}",
                    {"amount": amount_data, "error": str(e)},
                ) from e
        else:
            raise ConversionError(
                f"Unsupported money amount type: {type(amount_data)}",
                {"amount_data": amount_data, "type": str(type(amount_data))},
            )

    def _parse_extra_services(self, data: dict[str, Any]) -> list[ExtraService]:
        """Parse extra services from response."""
        services = []

        services_data = data.get("ExtraServices", [])
        if not isinstance(services_data, list):
            services_data = [services_data] if services_data else []

        # Extract currency from trip details data - NO FALLBACK for real money amounts
        default_currency = self._extract_currency_from_data(data)
        if not default_currency:
            self.logger.warning(
                "Cannot parse extra services: missing currency in trip details"
            )
            return services

        for service in services_data:
            if isinstance(service, dict):
                service_currency = service.get("Currency") or default_currency
                services.append(
                    ExtraService(
                        service_id=service.get("ServiceId", ""),
                        service_type=service.get("ServiceType", "OTHER"),
                        service_name=service.get("ServiceName", "Extra Service"),
                        description=service.get("Description", ""),
                        price=self._parse_money_amount(
                            service.get("Price"), service_currency
                        ),
                        currency=service_currency,
                        is_mandatory=service.get("IsMandatory", False),
                    )
                )

        return services

    def _parse_booking_notes(self, data: dict[str, Any]) -> list[BookingNote]:
        """Parse booking notes from response."""
        notes = []

        notes_data = data.get("BookingNotes", data.get("Notes", ""))

        if isinstance(notes_data, str) and notes_data:
            notes.append(
                BookingNote(
                    note_type="GENERAL",
                    note_text=notes_data,
                    created_date=datetime.now().isoformat(),
                )
            )
        elif isinstance(notes_data, list):
            for note in notes_data:
                if isinstance(note, dict):
                    notes.append(
                        BookingNote(
                            note_type=note.get("Type", "GENERAL"),
                            note_text=note.get("Text", ""),
                            created_date=note.get(
                                "CreatedDate", datetime.now().isoformat()
                            ),
                        )
                    )
                elif isinstance(note, str):
                    notes.append(
                        BookingNote(
                            note_type="GENERAL",
                            note_text=note,
                            created_date=datetime.now().isoformat(),
                        )
                    )

        return notes
