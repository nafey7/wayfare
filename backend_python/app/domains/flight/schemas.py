import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Self, TypeVar

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domains.common import (
    DateTime,
    Duration,
    EmailStr,
    ErrorDetails,
    MoneyAmount,
    PersonName,
)
from app.shared.flight_leg_summary import FlightLegSummary

from .enums import (
    BaggageUnit,
    BookingStatus,
    CabinClass,
    CabinClassText,
    CheckInLocation,
    FareRuleCategory,
    FareType,
    FlightAPIEnvironment,
    FrequentFlyerTier,
    JourneyType,
    MarriageGroup,
    MealCode,
    PassengerType,
    PNRStatus,
    RequiredBookingField,
    ServiceBehavior,
    ServiceType,
    TicketStatus,
    TicketType,
)
from .journey_params import coerce_legacy_flight_search_request_dict


# Temporary local models until proper domain refactoring
class PersonalInfo(BaseModel):
    """Personal information for travelers"""

    name: PersonName = Field(..., description="Full name")
    date_of_birth: str | None = Field(None, description="Date of birth")
    nationality: str | None = Field(None, description="Nationality")


class TravelDocuments(BaseModel):
    """Travel document information"""

    passport_number: str | None = Field(None, description="Passport number")
    passport_expiry: str | None = Field(None, description="Passport expiry date")
    passport_country: str | None = Field(None, description="Issuing country")


class ContactInformation(BaseModel):
    """Contact information"""

    email: EmailStr = Field(..., description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    area_code: str | None = Field(default=None, description="Area code")
    country_code: str | None = Field(default=None, description="Country code")


class PostalCode(BaseModel):
    """Postal code information"""

    code: str = Field(..., description="Postal code")
    country: str = Field(..., description="Country code")


# Type alias for date
Date = date

T = TypeVar("T")


# ==============================================================================
# FLIGHT-SPECIFIC DOMAIN SCHEMAS
# ==============================================================================


class TaxDetails(BaseModel):
    """Tax breakdown details"""

    tax_code: str = Field(..., description="Tax type code (e.g., 'YR', 'IN', 'K3')")
    tax_amount: MoneyAmount = Field(..., description="Tax amount details")


class AirportInfo(BaseModel):
    """Airport information with codes and names"""

    iata_code: str = Field(
        ..., description="3-letter IATA code (e.g., 'DEL', 'BOM', 'DXB')"
    )
    icao_code: str | None = Field(None, description="4-letter ICAO code (e.g., 'VIDP')")
    airport_name: str | None = Field(None, description="Full airport name")
    city_name: str | None = Field(None, description="City name")
    country_code: str | None = Field(
        None, description="ISO 3166-1 alpha-2 country code"
    )


class AirlineInfo(BaseModel):
    """Airline information with codes and names"""

    iata_code: str = Field(
        ..., description="2-letter IATA airline code (e.g., '6E', 'AI', 'BA')"
    )
    icao_code: str | None = Field(None, description="3-letter ICAO code (e.g., 'IGO')")
    airline_name: str | None = Field(
        None, description="Full airline name (e.g., 'IndiGo', 'Air India')"
    )
    logo_url: str | None = Field(
        None, description="URL to airline logo (from FlightLogic airline_list API)"
    )


class AircraftInfo(BaseModel):
    """Aircraft type and model information"""

    aircraft_type_code: str = Field(
        ..., description="Aircraft type code (e.g., '320', '737', 'M90')"
    )
    manufacturer: str | None = Field(
        None, description="Aircraft manufacturer (e.g., 'Airbus', 'Boeing')"
    )
    model_name: str | None = Field(
        None, description="Aircraft model (e.g., 'A320', '737-800')"
    )


class TerminalInfo(BaseModel):
    """Terminal information"""

    terminal_name: str = Field(
        ..., description="Terminal identifier (e.g., 'T1', 'Terminal 2', 'A')"
    )
    terminal_description: str | None = Field(None, description="Full terminal name")
    airport: AirportInfo = Field(..., description="Airport this terminal belongs to")


class RouteCode(BaseModel):
    """Route code information"""

    origin_code: str = Field(..., description="Origin airport IATA code")
    destination_code: str = Field(..., description="Destination airport IATA code")
    formatted_code: str = Field(..., description="Combined route code (e.g., 'DELDXB')")


class FlightNumber(BaseModel):
    """Flight number information"""

    airline_prefix: str = Field(..., description="Airline code (e.g., 'BA', '6E')")
    flight_number: str = Field(..., description="Flight number (e.g., '729', '6278')")
    formatted_number: str = Field(
        ..., description="Complete flight number (e.g., 'BA729', '6E6278')"
    )


class AirlinePNR(BaseModel):
    """Airline PNR information"""

    pnr_code: str = Field(..., description="PNR code (e.g., 'MKZNHA')")
    airline: AirlineInfo = Field(..., description="Airline that issued the PNR")
    status: PNRStatus | None = Field(None, description="PNR status")


class BookingClassCode(BaseModel):
    """Booking class code information"""

    class_code: str = Field(..., description="Booking class code (e.g., 'Y', 'V', 'X')")
    class_name: str | None = Field(
        None, description="Class description (e.g., 'Economy Saver')"
    )
    fare_basis: str | None = Field(None, description="Fare basis code")


class BaggageAllowanceInfo(BaseModel):
    """Baggage allowance information"""

    allowance_type: BaggageUnit = Field(..., description="Type of allowance")
    allowance_value: str = Field(
        ..., description="Allowance value (e.g., '25KG', '2P')"
    )
    description: str = Field(..., description="Human readable description")


class ServiceDescription(BaseModel):
    """Service description information"""

    description_text: str = Field(
        ..., description="Service description text (flexible for various services)"
    )
    category: str | None = Field(None, description="Service category hint")


class FareBasisCode(BaseModel):
    """Fare basis code information"""

    code: str = Field(..., description="Fare basis code (e.g., 'Y', 'S', 'C')")
    segment_number: int = Field(..., description="Segment this code applies to")
    description: str | None = Field(None, description="Human readable description")


class SeatAvailability(BaseModel):
    """Seat availability information"""

    available_seats: int = Field(..., description="Number of available seats")
    is_limited: bool = Field(..., description="True if limited availability")


class StopDetail(BaseModel):
    """Stop detail information"""

    stop_airport: AirportInfo = Field(..., description="Stop airport details")
    arrival_time: DateTime = Field(..., description="Arrival at stop")
    departure_time: DateTime = Field(..., description="Departure from stop")
    stop_duration: Duration = Field(..., description="Stop duration details")


class PenaltyDetails(BaseModel):
    """Penalty details for changes and cancellations"""

    is_cancellation_allowed: bool = Field(..., description="Can ticket be cancelled")
    cancellation_penalty: MoneyAmount = Field(..., description="Cancellation fee")
    is_change_allowed: bool = Field(..., description="Can ticket be changed")
    change_penalty: MoneyAmount = Field(..., description="Change fee")


class BookingNote(BaseModel):
    """Booking note information"""

    note_type: str | None = Field(
        None, description="Type of note (e.g., 'GENERAL', 'SPECIAL_REQUESTS')"
    )
    note_text: str = Field(..., description="Note content")
    created_at: DateTime | None = Field(None, description="When note was created")


class BookingNotes(BaseModel):
    """Structured booking notes"""

    notes: list[str] = Field(..., description="Array of note strings")
    instructions: str | None = Field(None, description="Special booking instructions")
    internal_remarks: str | None = Field(
        None, description="Internal processing remarks"
    )


# ======== BASE REQUEST SCHEMAS ========


class BaseFlightLogicRequest(BaseModel):
    """Base request with FlightLogic credentials (optional - will use config if not provided)"""

    user_id: str | None = Field(
        default=None, description="FlightLogic credentials (optional)"
    )
    user_password: str | None = Field(
        default=None, description="FlightLogic credentials (optional)"
    )
    access: FlightAPIEnvironment | None = Field(
        default=None, description="Environment type (optional)"
    )
    ip_address: str | None = Field(
        default=None, description="Client IP address (optional)"
    )


# ======== 1. SEARCH SCHEMAS ========


class TimeWindow(BaseModel):
    """Time window for departure/arrival filtering"""

    min: str = Field(..., description="Minimum time in HH:mm format")
    max: str = Field(..., description="Maximum time in HH:mm format")

    @field_validator("min", "max")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate that time is in HH:mm format (00:00-23:59)."""
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", v):
            raise ValueError(f"Time must be in HH:mm format (00:00-23:59), got '{v}'")
        return v


class LegFilter(BaseModel):
    """Leg-specific filter for journey segments"""

    leg_index: int = Field(
        ..., description="0 for outbound, 1 for inbound, 2+ for multi-city"
    )
    description: str | None = Field(None, description="Human-readable description")
    city_wise_search: bool | None = Field(
        None,
        description="If True, allows flights from/to any airport in the origin/destination city for this leg. "
        "If False or None, only exact airport matches are kept. Applies to both origin AND destination of the leg.",
    )
    departure_window: TimeWindow | None = None
    arrival_window: TimeWindow | None = None
    max_duration_minutes: int | None = None
    excluded_layover_airports: list[str] | None = None
    allowed_layover_airports: list[str] | None = None


class FlightSearchFilters(BaseModel):
    """Comprehensive filters for flight search results"""

    # Global filters
    # [DEPRECATED] Use journey_filters[].city_wise_search instead for per-leg control
    city_wise_search_origin: bool | None = Field(
        None,
        description="[DEPRECATED] Use journey_filters[].city_wise_search instead. "
        "If True, allows flights from any airport in the origin city. "
        "If False or None, only exact origin airport matches are kept.",
    )
    city_wise_search_destination: bool | None = Field(
        None,
        description="[DEPRECATED] Use journey_filters[].city_wise_search instead. "
        "If True, allows flights to any airport in the destination city. "
        "If False or None, only exact destination airport matches are kept.",
    )
    min_price: float | None = None
    max_price: float | None = None
    is_refundable: bool | None = None
    carrier: Literal["GDS", "LCC"] | None = None
    max_stops: int | None = None
    operating_airlines: list[str] | None = None

    # Leg-specific filters
    journey_filters: list[LegFilter] | None = None


class OriginDestinationSegment(BaseModel):
    """Origin destination segment for search"""

    departure_date: Date = Field(..., description="Departure date")
    return_date: Date | None = Field(
        None,
        description="Deprecated for new clients: use two origin_destination_info rows for Return. "
        "If set on a single row with journey_type Return, the server splits into two legs.",
    )
    origin_airport: AirportInfo = Field(..., description="Origin airport details")
    destination_airport: AirportInfo = Field(
        ..., description="Destination airport details"
    )


class FlightSearchRequest(BaseFlightLogicRequest):
    """Flight search request schema"""

    required_currency_code: str | None = Field(
        None, description="Preferred currency ISO 4217 code (e.g., 'USD', 'EUR')"
    )
    journey_type: JourneyType = Field(
        ...,
        description="OneWay = one origin-destination row in origin_destination_info; "
        "Return = round trip (exactly two rows, A→B then B→A); "
        "Circle = multi-city (at least two rows with connecting airports). "
        "Legacy alias: RoundTrip is normalized to Return.",
    )
    origin_destination_info: list[OriginDestinationSegment] = Field(
        ...,
        description="Search legs (O&D rows). One row for OneWay; two for Return (outbound then inbound); "
        "two or more for Circle with each leg's origin matching the previous leg's destination.",
    )
    cabin_class: CabinClass = Field(..., description="Cabin class")
    adults: int = Field(..., description="Number of adults", ge=0)
    children: int = Field(..., description="Number of children", ge=0)
    infants: int = Field(..., description="Number of infants", ge=0)
    preferred_airline: AirlineInfo | None = Field(
        None, description="Preferred airline for search"
    )
    direct_flight: int | None = Field(
        None, description="0 = all flights, 1 = only direct flights"
    )
    city_wise_search_origin: bool | None = Field(
        None,
        description="[DEPRECATED] Use filters.city_wise_search_origin instead. "
        "If True, don't filter by exact origin airport code (allow all airports in city). "
        "If False or absent, filter to exact origin airport code match.",
    )
    city_wise_search_destination: bool | None = Field(
        None,
        description="[DEPRECATED] Use filters.city_wise_search_destination instead. "
        "If True, don't filter by exact destination airport code (allow all airports in city). "
        "If False or absent, filter to exact destination airport code match.",
    )
    filters: FlightSearchFilters | None = Field(
        None, description="Filters to apply to search results"
    )
    revalidate_flights_count: int | None = Field(
        None,
        ge=0,
        le=10,
        description="Number of flights to revalidate after search; 0 or omitted skips revalidation",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_legacy_flight_search_request(cls, data: Any) -> Any:
        """Normalize RoundTrip and deprecated single-row Return (+ return_date) payloads."""
        if not isinstance(data, dict):
            return data
        return coerce_legacy_flight_search_request_dict(data)

    @model_validator(mode="after")
    def validate_passenger_limits(self) -> "FlightSearchRequest":
        """Validate passenger count business rules.

        Rules:
        1. At least 1 passenger required
        2. Total passengers cannot exceed 9
        3. Infant count cannot exceed combined Adults + Children count
        4. At least 1 adult required when infants are present
        """
        total_passengers = self.adults + self.children + self.infants

        # Rule 1: At least 1 passenger required
        if total_passengers == 0:
            raise ValueError("At least 1 passenger is required for flight search.")

        # Rule 2: Total passengers cannot exceed 9
        if total_passengers > 9:
            raise ValueError(
                f"Total passenger count cannot exceed 9. Current: {total_passengers} "
                f"(Adults: {self.adults}, Children: {self.children}, Infants: {self.infants})"
            )

        # Rule 3: Infant count cannot exceed combined Adults + Children count
        if self.infants > (self.adults + self.children):
            raise ValueError(
                f"Infant count ({self.infants}) cannot exceed combined Adults + Children count ({self.adults + self.children}). "
                f"Each infant must be accompanied by an adult or child."
            )

        # Rule 4: At least 1 adult required when infants are present
        if self.infants > 0 and self.adults == 0:
            raise ValueError(
                f"Infants ({self.infants}) cannot travel without an accompanying adult. At least 1 adult is required."
            )

        return self

    @model_validator(mode="after")
    def merge_legacy_filters(self) -> "FlightSearchRequest":
        """Merge legacy city_wise_search fields into filters for backward compatibility.

        If filters is None, create it. If city_wise_search_* fields are provided at top level,
        they take precedence over filters (for backward compatibility).
        """
        # Initialize filters if not present
        if self.filters is None:
            self.filters = FlightSearchFilters()  # type: ignore[call-arg]

        # Merge top-level city_wise fields into filters (top-level takes precedence)
        if self.city_wise_search_origin is not None:
            self.filters.city_wise_search_origin = self.city_wise_search_origin
        if self.city_wise_search_destination is not None:
            self.filters.city_wise_search_destination = (
                self.city_wise_search_destination
            )

        return self

    @model_validator(mode="after")
    def validate_journey_type_and_segments(self) -> "FlightSearchRequest":
        """Enforce segment count and routing rules per journey type (FlightLogic contract)."""
        ods = self.origin_destination_info
        jt = self.journey_type

        if not ods:
            raise ValueError(
                "origin_destination_info must contain at least one segment."
            )

        if jt == JourneyType.ONE_WAY:
            if len(ods) != 1:
                raise ValueError(
                    f"OneWay journey requires exactly one origin-destination segment; got {len(ods)}."
                )
            if any(seg.return_date is not None for seg in ods):
                raise ValueError(
                    "return_date must not be set on segments for OneWay journeys."
                )
        elif jt == JourneyType.RETURN:
            if len(ods) != 2:
                raise ValueError(
                    f"Return journey requires exactly two origin-destination segments; got {len(ods)}."
                )
            if any(seg.return_date is not None for seg in ods):
                raise ValueError(
                    "return_date must not be set on segments for Return journeys "
                    "(use the second segment's departure_date for the inbound flight)."
                )
            a0 = ods[0].origin_airport.iata_code.upper()
            d0 = ods[0].destination_airport.iata_code.upper()
            a1 = ods[1].origin_airport.iata_code.upper()
            d1 = ods[1].destination_airport.iata_code.upper()
            if a1 != d0 or d1 != a0:
                raise ValueError(
                    "Return journey segments must form a round trip: the second segment must "
                    "depart from the first destination and return to the first origin."
                )
            if ods[1].departure_date < ods[0].departure_date:
                raise ValueError(
                    "Inbound departure_date must be on or after outbound departure_date."
                )
        elif jt == JourneyType.CIRCLE:
            if len(ods) < 2:
                raise ValueError(
                    f"Circle (multi-city) journey requires at least two origin-destination segments; "
                    f"got {len(ods)}."
                )
            if any(seg.return_date is not None for seg in ods):
                raise ValueError(
                    "return_date must not be set on segments for Circle journeys."
                )
            # Connected-segments + sequential-date rules apply only when the
            # search will be sent to FlightLogic as a single Circle request.
            # When MULTICITY_PARALLEL_SEARCH is on (default), each leg is
            # executed as an independent OneWay search, so open-jaw itineraries
            # (e.g. fly into Palermo, ground transport to Catania, fly out) are
            # legitimate. Skip the strict checks in that mode.
            from app.core.config import settings

            if not settings.MULTICITY_PARALLEL_SEARCH:
                for i in range(len(ods) - 1):
                    dest_i = ods[i].destination_airport.iata_code.upper()
                    orig_next = ods[i + 1].origin_airport.iata_code.upper()
                    if dest_i != orig_next:
                        raise ValueError(
                            f"Circle journey segments must connect: destination of leg {i + 1} ({dest_i}) "
                            f"must match origin of leg {i + 2} ({orig_next})."
                        )
                    if ods[i + 1].departure_date < ods[i].departure_date:
                        raise ValueError(
                            f"Each leg's departure_date must be on or after the previous leg's date "
                            f"(leg {i + 2} is before leg {i + 1})."
                        )
        return self


class FlightSegment(BaseModel):
    """Individual flight segment"""

    arrival_airport: AirportInfo = Field(..., description="Arrival airport details")
    arrival_datetime: DateTime = Field(..., description="Arrival date and time")
    departure_airport: AirportInfo = Field(..., description="Departure airport details")
    departure_datetime: DateTime = Field(..., description="Departure date and time")
    cabin_class: CabinClass = Field(..., description="Cabin class type")
    cabin_class_text: CabinClassText | None = Field(
        None, description="LCC cabin class text"
    )
    e_ticket: bool = Field(..., description="E-ticket availability")
    flight_duration: Duration = Field(..., description="Flight duration details")
    marketing_flight_number: FlightNumber = Field(
        ..., description="Marketing flight details"
    )
    marketing_airline: AirlineInfo = Field(..., description="Marketing airline details")
    marriage_group: MarriageGroup | None = Field(None, description="Marriage indicator")
    meal_code: MealCode | None = Field(None, description="Meal preference")
    operating_airline: AirlineInfo = Field(..., description="Operating airline details")
    operating_flight_number: FlightNumber = Field(
        ..., description="Operating flight details"
    )
    aircraft: AircraftInfo | None = Field(None, description="Aircraft details")
    booking_class_code: BookingClassCode | None = Field(
        None, description="Booking class details"
    )
    segment_stops: int = Field(..., description="Stops within this segment")
    stop_details: list[StopDetail] | None = Field(None, description="Details per stop")
    seat_availability: SeatAvailability = Field(..., description="Seat availability")


class FlightLeg(BaseModel):
    """Flight leg containing multiple segments"""

    total_stops: int = Field(..., description="Number of stops in this leg")
    flight_segments: list[FlightSegment] = Field(
        ..., description="Individual flight segments"
    )


class FareTotals(BaseModel):
    """Fare totals breakdown"""

    base_fare: MoneyAmount = Field(..., description="Base fare amount")
    equivalent_fare: MoneyAmount = Field(
        ..., description="Equivalent fare in booking currency"
    )
    service_tax: MoneyAmount = Field(..., description="Service tax amount")
    total_tax: MoneyAmount = Field(..., description="Total taxes")
    total_fare: MoneyAmount = Field(..., description="Grand total (with platform fee)")
    original_total_fare: MoneyAmount | None = Field(
        None,
        description="Original total fare before platform fee (for frontend calculation)",
    )
    platform_fee_percentage: float | None = Field(
        None,
        description="Platform fee percentage (e.g., 5.0 for 5%)",
    )


class PassengerTypeInfo(BaseModel):
    """Passenger type information"""

    passenger_type: PassengerType = Field(..., description="Passenger type")
    passenger_count: int = Field(..., description="Number of passengers")


class IndividualPassengerFare(BaseModel):
    """Individual passenger fare breakdown"""

    base_fare: MoneyAmount = Field(..., description="Base fare per passenger")
    equivalent_fare: MoneyAmount | None = Field(
        None, description="Equivalent fare per passenger"
    )
    service_tax: MoneyAmount = Field(..., description="Service tax per passenger")
    surcharges: MoneyAmount | None = Field(None, description="Surcharges per passenger")
    tax_breakdown: list[TaxDetails] = Field(..., description="Tax breakdown")
    total_tax: MoneyAmount = Field(..., description="Total tax per passenger")
    total_fare: MoneyAmount = Field(..., description="Total per passenger")


class BaggageAllowance(BaseModel):
    """Baggage allowance per segment"""

    # FlightLogic API fields
    baggage_id: str | None = Field(None, description="Baggage ID")
    baggage_pieces: int | None = Field(None, description="Number of pieces allowed")
    baggage_weight: float | None = Field(None, description="Weight allowance")
    baggage_unit: str | None = Field(None, description="Unit of weight (KG/LB)")

    # Alternative fields for compatibility
    segment_number: int | None = Field(
        None, description="Flight segment this applies to"
    )
    allowance_info: BaggageAllowanceInfo | None = Field(
        None, description="Baggage allowance details"
    )
    additional_notes: str | None = Field(None, description="Additional notes")


class CabinBaggageAllowance(BaseModel):
    """Cabin baggage allowance per segment"""

    # FlightLogic API fields
    cabin_baggage_id: str | None = Field(None, description="Cabin baggage ID")
    cabin_baggage_pieces: int | None = Field(
        None, description="Number of cabin pieces allowed"
    )
    cabin_baggage_weight: float | None = Field(
        None, description="Cabin weight allowance"
    )
    cabin_baggage_unit: str | None = Field(None, description="Unit of weight (KG/LB)")

    # Alternative fields for compatibility
    segment_number: int | None = Field(
        None, description="Flight segment this applies to"
    )
    allowance_info: BaggageAllowanceInfo | None = Field(
        None, description="Cabin baggage allowance details"
    )
    additional_notes: str | None = Field(None, description="Additional notes")


class PassengerFareBreakdown(BaseModel):
    """Passenger fare breakdown per type"""

    passenger_type_info: PassengerTypeInfo = Field(
        ..., description="Passenger type information"
    )
    fare_basis_codes: list[FareBasisCode] | None = Field(
        None, description="Fare codes per segment"
    )
    individual_passenger_fare: IndividualPassengerFare = Field(
        ..., description="Individual fare breakdown"
    )
    baggage_allowance: list[BaggageAllowance] = Field(
        ..., description="Per segment baggage info"
    )
    cabin_baggage_allowance: list[CabinBaggageAllowance] = Field(
        ..., description="Per segment cabin baggage info"
    )
    penalty_details: PenaltyDetails | None = Field(
        None, description="Change/cancellation penalties"
    )


class FarePricing(BaseModel):
    """Fare pricing details"""

    has_mixed_booking_classes: bool = Field(
        ..., description="Different booking classes for passengers"
    )
    fare_source_code: str = Field(..., description="Unique fare ID for booking")
    fare_type: FareType = Field(..., description="Fare type")
    is_refundable: bool = Field(..., description="Refund policy")
    fare_totals: FareTotals = Field(..., description="Total pricing breakdown")
    passenger_fare_breakdown: list[PassengerFareBreakdown] = Field(
        ..., description="Per passenger type breakdown"
    )


class FareItinerary(BaseModel):
    """Fare itinerary with flights and pricing"""

    journey_type: JourneyType = Field(..., description="Journey type")
    requires_passport: bool | None = Field(None, description="Passport required")
    sequence_number: str | None = Field(None, description="Sequence identifier")
    ticket_type: TicketType = Field(..., description="Ticket type")
    validating_airline: AirlineInfo = Field(..., description="Airline issuing ticket")
    flight_legs: list[FlightLeg] = Field(..., description="Flight legs")
    pricing: FarePricing = Field(..., description="Pricing details")


class MulticityLegSearchResult(BaseModel):
    """One leg of a parallel multicity (Circle) search; each leg has its own FlightLogic session."""

    leg_index: int = Field(
        ..., ge=0, description="0-based leg index in origin_destination_info"
    )
    origin: str = Field(..., description="Origin airport IATA from the search segment")
    destination: str = Field(
        ..., description="Destination airport IATA from the search segment"
    )
    departure_date: date = Field(
        ..., description="Departure date for this leg (echo from request)"
    )
    session_id: str = Field(
        default="",
        description="FlightLogic session for this leg; empty when the leg search failed",
    )
    supplier: str = Field(
        default="",
        description="Supplier name for this leg; empty when the leg search failed",
    )
    fare_itineraries: list[FareItinerary] = Field(
        default_factory=list,
        description="One-way results for this leg",
    )
    inbound_fare_itineraries: list[FareItinerary] | None = Field(
        None,
        description="Usually None for per-leg OneWay search",
    )
    errors: list[ErrorDetails] | None = Field(
        None,
        description="Errors for this leg only; other legs may still succeed",
    )


class FlightSearchResponse(BaseModel):
    """Flight search response schema"""

    session_id: str = Field(
        ...,
        description="Base64 encoded session for subsequent operations; empty when multicity_legs is used",
    )
    supplier: str = Field(..., description="Supplier name")
    fare_itineraries: list[FareItinerary] = Field(
        ..., description="Outbound/oneway flights"
    )
    inbound_fare_itineraries: list[FareItinerary] | None = Field(
        None, description="Indian domestic roundtrips only"
    )
    errors: list[ErrorDetails] | None = Field(None, description="Error details if any")
    multicity_legs: list[MulticityLegSearchResult] | None = Field(
        None,
        description="When Circle is searched as parallel OneWay legs, one result per leg with per-leg session_id",
    )


class FlightSegmentDTO(BaseModel):
    """Individual flight segment (single flight between two airports).

    Used to represent each leg of a multi-stop journey. Has the same interface
    as FlightSummaryDTO for consistency in frontend rendering.
    """

    airline: str = Field("", description="Airline name")
    airline_code: str = Field("", description="IATA airline code")
    flight_number: str = Field("", description="Flight number (e.g., BA1234)")
    departure_date: str = Field("", description="Departure date (YYYY-MM-DD)")
    departure_time: str = Field("", description="Departure time (HH:MM)")
    arrival_date: str = Field("", description="Arrival date (YYYY-MM-DD)")
    arrival_time: str = Field("", description="Arrival time (HH:MM)")
    duration: str = Field("", description="Segment duration (e.g., 2h 30m)")
    duration_minutes: int = Field(0, description="Segment duration in minutes")
    origin_code: str = Field("", description="Origin airport IATA code")
    origin_city: str = Field("", description="Origin city name")
    origin_airport: str = Field("", description="Origin airport name")
    destination_code: str = Field("", description="Destination airport IATA code")
    destination_city: str = Field("", description="Destination city name")
    destination_airport: str = Field("", description="Destination airport name")
    aircraft_type: str = Field("", description="Aircraft type code (e.g., 77W, 320)")
    cabin_class: str = Field("", description="Cabin class (e.g., Economy, Business)")


class FlightSummaryDTO(BaseModel):
    """Simplified flight summary for frontend display.

    This DTO extracts the essential information from a FareItinerary for use in
    chat responses, search results cards, and booking flows. It flattens the
    nested FareItinerary -> FlightLeg -> FlightSegment structure into a simple dict.

    Usage:
        flight_summary = FlightSummaryDTO.from_fare_itinerary(fare_itinerary)
        # Returns dict via .model_dump() or use directly as Pydantic model
    """

    id: str = Field("", description="Fare source code (unique identifier)")
    airline: str = Field("", description="Airline name")
    airline_code: str = Field("", description="IATA airline code")
    flight_number: str = Field("", description="Flight number (e.g., BA1234)")
    departure_date: str = Field("", description="Departure date (YYYY-MM-DD)")
    departure_time: str = Field("", description="Departure time (HH:MM)")
    arrival_date: str = Field("", description="Arrival date (YYYY-MM-DD)")
    arrival_time: str = Field("", description="Arrival time (HH:MM)")
    duration: str = Field("", description="Flight duration (e.g., 8h 30m)")
    duration_minutes: int = Field(0, description="Flight duration in minutes")
    stops: int = Field(0, description="Number of stops")
    price: float = Field(0, description="Total price")
    currency: str = Field("USD", description="Currency code")
    original_total_fare: float | None = Field(
        None,
        description="Original total fare before platform fee (for frontend breakdown)",
    )
    origin_code: str = Field("", description="Origin airport IATA code")
    origin_city: str = Field("", description="Origin city name")
    origin_airport: str = Field("", description="Origin airport name")
    destination_code: str = Field("", description="Destination airport IATA code")
    destination_city: str = Field("", description="Destination city name")
    destination_airport: str = Field("", description="Destination airport name")
    category: str | None = Field(None, description="Category label (cheapest, fastest)")
    segments: list["FlightSegmentDTO"] = Field(
        default_factory=list,
        description="Individual flight segments ordered by departure time",
    )

    @classmethod
    def from_fare_itinerary(
        cls,
        flight: "FareItinerary",
        category: str | None = None,
        airport_info: dict[str, dict[str, str]] | None = None,
    ) -> "FlightSummaryDTO":
        """Create FlightSummaryDTO from a FareItinerary object.

        Args:
            flight: FareItinerary Pydantic model from FlightLogic API
            category: Optional category label (cheapest, fastest, best_value)
            airport_info: Optional dict mapping IATA codes to city/name info

        Returns:
            FlightSummaryDTO instance
        """
        airport_info = airport_info or {}

        # Extract fare_source_code from pricing
        fare_source_code = ""
        if hasattr(flight, "pricing") and flight.pricing:
            fare_source_code = getattr(flight.pricing, "fare_source_code", "") or ""

        # Extract pricing information
        price = 0.0
        currency = "USD"
        original_total_fare = None
        if hasattr(flight, "pricing") and flight.pricing:
            pricing = flight.pricing
            if hasattr(pricing, "fare_totals") and pricing.fare_totals:
                fare_totals = pricing.fare_totals
                total_fare = getattr(fare_totals, "total_fare", None)
                if total_fare:
                    amount = getattr(total_fare, "amount", 0)
                    # Defensive check: ensure amount is a number/string/Decimal, not a Mock object
                    if isinstance(amount, (int, float, str, Decimal)):
                        price = float(amount)
                    else:
                        price = 0.0
                    currency = (
                        getattr(total_fare, "currency_code", None)
                        or getattr(total_fare, "currency", None)
                        or "USD"
                    )
                # Extract original_total_fare if available
                original_fare = getattr(fare_totals, "original_total_fare", None)
                if original_fare:
                    amount = getattr(original_fare, "amount", 0)
                    # Defensive check: ensure amount is a number/string/Decimal, not a Mock object
                    if isinstance(amount, (int, float, str, Decimal)):
                        original_total_fare = float(amount)
                    else:
                        original_total_fare = None

        # Extract airline info from validating_airline
        airline = ""
        airline_code = ""
        if hasattr(flight, "validating_airline") and flight.validating_airline:
            airline = getattr(flight.validating_airline, "airline_name", "") or ""
            airline_code = getattr(flight.validating_airline, "iata_code", "") or ""

        # Initialize result with defaults - typed as dict[str, Any] for mypy
        result: dict[str, Any] = {
            "id": fare_source_code,
            "airline": airline,
            "airline_code": airline_code,
            "flight_number": "",
            "departure_date": "",
            "departure_time": "",
            "arrival_date": "",
            "arrival_time": "",
            "duration": "",
            "duration_minutes": 0,
            "stops": 0,
            "price": price,
            "currency": currency,
            "original_total_fare": original_total_fare,
            "origin_code": "",
            "origin_city": "",
            "origin_airport": "",
            "destination_code": "",
            "destination_city": "",
            "destination_airport": "",
            "category": category,
            "segments": [],
        }

        # Extract from flight legs and segments
        if hasattr(flight, "flight_legs") and flight.flight_legs:
            first_leg = flight.flight_legs[0]
            last_leg = flight.flight_legs[-1]

            # Get first and last segments
            first_segment = None
            last_segment = None

            if hasattr(first_leg, "flight_segments") and first_leg.flight_segments:
                first_segment = first_leg.flight_segments[0]
            if hasattr(last_leg, "flight_segments") and last_leg.flight_segments:
                last_segment = last_leg.flight_segments[-1]

            # Extract from first segment
            if first_segment:
                # Airline info from marketing_airline (overrides validating_airline)
                if hasattr(first_segment, "marketing_airline"):
                    mkt_airline = first_segment.marketing_airline
                    result["airline_code"] = (
                        getattr(mkt_airline, "iata_code", "") or result["airline_code"]
                    )
                    result["airline"] = (
                        getattr(mkt_airline, "airline_name", "") or result["airline"]
                    )

                # Flight number
                if hasattr(first_segment, "marketing_flight_number"):
                    flight_num = first_segment.marketing_flight_number
                    if hasattr(flight_num, "formatted_number"):
                        result["flight_number"] = flight_num.formatted_number or ""
                    else:
                        carrier = getattr(flight_num, "carrier_code", "") or ""
                        number = getattr(flight_num, "flight_number", "") or ""
                        result["flight_number"] = f"{carrier}{number}"

                # Origin airport
                if hasattr(first_segment, "departure_airport"):
                    dep_airport = first_segment.departure_airport
                    result["origin_code"] = getattr(dep_airport, "iata_code", "") or ""
                    result["origin_city"] = getattr(dep_airport, "city_name", "") or ""
                    result["origin_airport"] = (
                        getattr(dep_airport, "airport_name", "") or ""
                    )
                    # Fallback to airport_info lookup
                    if (
                        not result["origin_city"]
                        and result["origin_code"] in airport_info
                    ):
                        result["origin_city"] = airport_info[result["origin_code"]].get(
                            "city", ""
                        )
                    if (
                        not result["origin_airport"]
                        and result["origin_code"] in airport_info
                    ):
                        result["origin_airport"] = airport_info[
                            result["origin_code"]
                        ].get("name", "")

                # Departure datetime
                if hasattr(first_segment, "departure_datetime"):
                    dep_dt = first_segment.departure_datetime
                    actual_dt = (
                        getattr(dep_dt, "value", dep_dt)
                        if hasattr(dep_dt, "value")
                        else dep_dt
                    )
                    if actual_dt:
                        if hasattr(actual_dt, "strftime"):
                            result["departure_date"] = actual_dt.strftime("%Y-%m-%d")
                            result["departure_time"] = actual_dt.strftime("%H:%M")
                        elif isinstance(actual_dt, str):
                            result["departure_date"] = actual_dt[:10]
                            result["departure_time"] = actual_dt[11:16]

            # Extract from last segment
            if last_segment:
                # Destination airport
                if hasattr(last_segment, "arrival_airport"):
                    arr_airport = last_segment.arrival_airport
                    result["destination_code"] = (
                        getattr(arr_airport, "iata_code", "") or ""
                    )
                    result["destination_city"] = (
                        getattr(arr_airport, "city_name", "") or ""
                    )
                    result["destination_airport"] = (
                        getattr(arr_airport, "airport_name", "") or ""
                    )
                    # Fallback to airport_info lookup
                    if (
                        not result["destination_city"]
                        and result["destination_code"] in airport_info
                    ):
                        result["destination_city"] = airport_info[
                            result["destination_code"]
                        ].get("city", "")
                    if (
                        not result["destination_airport"]
                        and result["destination_code"] in airport_info
                    ):
                        result["destination_airport"] = airport_info[
                            result["destination_code"]
                        ].get("name", "")

                # Arrival datetime
                if hasattr(last_segment, "arrival_datetime"):
                    arr_dt = last_segment.arrival_datetime
                    actual_dt = (
                        getattr(arr_dt, "value", arr_dt)
                        if hasattr(arr_dt, "value")
                        else arr_dt
                    )
                    if actual_dt:
                        if hasattr(actual_dt, "strftime"):
                            result["arrival_date"] = actual_dt.strftime("%Y-%m-%d")
                            result["arrival_time"] = actual_dt.strftime("%H:%M")
                        elif isinstance(actual_dt, str):
                            result["arrival_date"] = actual_dt[:10]
                            result["arrival_time"] = actual_dt[11:16]

            # Calculate total stops
            total_stops = 0
            for leg in flight.flight_legs:
                total_stops += getattr(leg, "total_stops", 0)
                if hasattr(leg, "flight_segments") and leg.flight_segments:
                    total_stops += len(leg.flight_segments) - 1
            result["stops"] = total_stops

            # Calculate total journey duration from departure to arrival timestamps
            # This correctly accounts for layover time, not just flight time
            total_duration = 0

            if first_segment and last_segment:
                # Extract departure datetime
                dep_dt_val = None
                if hasattr(first_segment, "departure_datetime"):
                    raw_dep = first_segment.departure_datetime
                    dep_dt_val = (
                        getattr(raw_dep, "value", raw_dep)
                        if hasattr(raw_dep, "value")
                        else raw_dep
                    )

                # Extract arrival datetime
                arr_dt_val = None
                if hasattr(last_segment, "arrival_datetime"):
                    raw_arr = last_segment.arrival_datetime
                    arr_dt_val = (
                        getattr(raw_arr, "value", raw_arr)
                        if hasattr(raw_arr, "value")
                        else raw_arr
                    )

                # Calculate duration if both timestamps are available
                if dep_dt_val and arr_dt_val:
                    # Parse strings to datetime if needed
                    if isinstance(dep_dt_val, str):
                        # Handle ISO format like "2026-02-06T20:00:00Z"
                        dep_dt_val = datetime.fromisoformat(
                            dep_dt_val.replace("Z", "+00:00")
                        )
                    if isinstance(arr_dt_val, str):
                        arr_dt_val = datetime.fromisoformat(
                            arr_dt_val.replace("Z", "+00:00")
                        )

                    # Calculate if both are datetime objects
                    if isinstance(dep_dt_val, datetime) and isinstance(
                        arr_dt_val, datetime
                    ):
                        diff = arr_dt_val - dep_dt_val
                        total_duration = int(diff.total_seconds() / 60)

            # Fallback: sum segment durations if timestamp calculation failed
            if total_duration <= 0:
                for leg in flight.flight_legs:
                    if hasattr(leg, "flight_segments") and leg.flight_segments:
                        for segment in leg.flight_segments:
                            if hasattr(segment, "flight_duration"):
                                seg_duration = segment.flight_duration
                                total_duration += getattr(
                                    seg_duration, "total_minutes", 0
                                )

            result["duration_minutes"] = total_duration
            if total_duration > 0:
                hours = total_duration // 60
                minutes = total_duration % 60
                if minutes > 0:
                    result["duration"] = f"{hours}h {minutes}m"
                else:
                    result["duration"] = f"{hours}h"

            # Extract all segments ordered by departure time
            all_segments: list[dict[str, Any]] = []
            for leg in flight.flight_legs:
                if hasattr(leg, "flight_segments") and leg.flight_segments:
                    for seg in leg.flight_segments:
                        segment_data = cls._extract_segment(seg, airport_info)
                        all_segments.append(segment_data)

            # Sort segments by departure datetime
            all_segments.sort(
                key=lambda s: (s.get("departure_date", ""), s.get("departure_time", ""))
            )
            result["segments"] = all_segments

        return cls(**result)

    @staticmethod
    def _extract_segment(
        segment: Any, airport_info: dict[str, dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Extract segment data from a FlightSegment object."""
        airport_info = airport_info or {}

        # Extract airline info
        seg_airline = ""
        seg_airline_code = ""
        if hasattr(segment, "marketing_airline") and segment.marketing_airline:
            seg_airline = getattr(segment.marketing_airline, "airline_name", "") or ""
            seg_airline_code = getattr(segment.marketing_airline, "iata_code", "") or ""

        # Flight number
        seg_flight_number = ""
        if hasattr(segment, "marketing_flight_number"):
            flight_num = segment.marketing_flight_number
            if hasattr(flight_num, "formatted_number"):
                seg_flight_number = flight_num.formatted_number or ""
            else:
                carrier = getattr(flight_num, "carrier_code", "") or ""
                number = getattr(flight_num, "flight_number", "") or ""
                seg_flight_number = f"{carrier}{number}"

        # Departure info
        seg_departure_date = ""
        seg_departure_time = ""
        if hasattr(segment, "departure_datetime"):
            dep_dt = segment.departure_datetime
            actual_dt = (
                getattr(dep_dt, "value", dep_dt) if hasattr(dep_dt, "value") else dep_dt
            )
            if actual_dt:
                if hasattr(actual_dt, "strftime"):
                    seg_departure_date = actual_dt.strftime("%Y-%m-%d")
                    seg_departure_time = actual_dt.strftime("%H:%M")
                elif isinstance(actual_dt, str):
                    seg_departure_date = actual_dt[:10]
                    seg_departure_time = actual_dt[11:16]

        # Origin airport
        seg_origin_code = ""
        seg_origin_city = ""
        seg_origin_airport = ""
        if hasattr(segment, "departure_airport") and segment.departure_airport:
            dep_airport = segment.departure_airport
            seg_origin_code = getattr(dep_airport, "iata_code", "") or ""
            seg_origin_city = getattr(dep_airport, "city_name", "") or ""
            seg_origin_airport = getattr(dep_airport, "airport_name", "") or ""
            # Fallback to airport_info lookup
            if not seg_origin_city and seg_origin_code in airport_info:
                seg_origin_city = airport_info[seg_origin_code].get("city", "")
            if not seg_origin_airport and seg_origin_code in airport_info:
                seg_origin_airport = airport_info[seg_origin_code].get("name", "")

        # Arrival info
        seg_arrival_date = ""
        seg_arrival_time = ""
        if hasattr(segment, "arrival_datetime"):
            arr_dt = segment.arrival_datetime
            actual_dt = (
                getattr(arr_dt, "value", arr_dt) if hasattr(arr_dt, "value") else arr_dt
            )
            if actual_dt:
                if hasattr(actual_dt, "strftime"):
                    seg_arrival_date = actual_dt.strftime("%Y-%m-%d")
                    seg_arrival_time = actual_dt.strftime("%H:%M")
                elif isinstance(actual_dt, str):
                    seg_arrival_date = actual_dt[:10]
                    seg_arrival_time = actual_dt[11:16]

        # Destination airport
        seg_destination_code = ""
        seg_destination_city = ""
        seg_destination_airport = ""
        if hasattr(segment, "arrival_airport") and segment.arrival_airport:
            arr_airport = segment.arrival_airport
            seg_destination_code = getattr(arr_airport, "iata_code", "") or ""
            seg_destination_city = getattr(arr_airport, "city_name", "") or ""
            seg_destination_airport = getattr(arr_airport, "airport_name", "") or ""
            # Fallback to airport_info lookup
            if not seg_destination_city and seg_destination_code in airport_info:
                seg_destination_city = airport_info[seg_destination_code].get(
                    "city", ""
                )
            if not seg_destination_airport and seg_destination_code in airport_info:
                seg_destination_airport = airport_info[seg_destination_code].get(
                    "name", ""
                )

        # Duration
        seg_duration_minutes = 0
        seg_duration = ""
        if hasattr(segment, "flight_duration") and segment.flight_duration:
            seg_duration_minutes = (
                getattr(segment.flight_duration, "total_minutes", 0) or 0
            )
            if seg_duration_minutes > 0:
                hours = seg_duration_minutes // 60
                minutes = seg_duration_minutes % 60
                seg_duration = f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"

        # Aircraft type
        seg_aircraft_type = ""
        if hasattr(segment, "aircraft") and segment.aircraft:
            aircraft_code = getattr(segment.aircraft, "aircraft_type_code", None)
            if aircraft_code and isinstance(aircraft_code, str):
                seg_aircraft_type = aircraft_code

        # Cabin class
        seg_cabin_class = ""
        if hasattr(segment, "cabin_class"):
            cabin = segment.cabin_class
            if cabin and isinstance(cabin, str):
                seg_cabin_class = cabin

        return {
            "airline": seg_airline,
            "airline_code": seg_airline_code,
            "flight_number": seg_flight_number,
            "departure_date": seg_departure_date,
            "departure_time": seg_departure_time,
            "arrival_date": seg_arrival_date,
            "arrival_time": seg_arrival_time,
            "duration": seg_duration,
            "duration_minutes": seg_duration_minutes,
            "origin_code": seg_origin_code,
            "origin_city": seg_origin_city,
            "origin_airport": seg_origin_airport,
            "destination_code": seg_destination_code,
            "destination_city": seg_destination_city,
            "destination_airport": seg_destination_airport,
            "aircraft_type": seg_aircraft_type,
            "cabin_class": seg_cabin_class,
        }


# ======== 2. FARE RULES SCHEMAS ========


class FlightFareRulesRequest(BaseModel):
    """Flight fare rules request"""

    session_id: str = Field(..., description="Token from availability search")
    fare_source_code: str = Field(..., description="Unique fare identification code")
    inbound_fare_source_code: str | None = Field(
        None, description="Indian domestic roundtrips only"
    )


class BaggageInformation(BaseModel):
    """Baggage information per flight"""

    flight_number: FlightNumber = Field(..., description="Operating flight details")
    departure_airport: AirportInfo = Field(..., description="Departure airport details")
    arrival_airport: AirportInfo = Field(..., description="Arrival airport details")
    baggage_allowance_code: BaggageUnit = Field(
        ..., description="Baggage allowance method"
    )


class FareRuleDetails(BaseModel):
    """Fare rule details"""

    airline: AirlineInfo = Field(..., description="Airline details")
    route_code: RouteCode | None = Field(
        None, description="Origin+destination route code"
    )
    rule_category: FareRuleCategory | None = Field(None, description="Rule category")
    rule_description: str | None = Field(
        None, description="Full text description of rules"
    )


class InboundFareData(BaseModel):
    """Inbound fare data for roundtrips"""

    baggage_information: list[BaggageInformation] = Field(
        ..., description="Baggage rules for inbound"
    )
    fare_rules: list[FareRuleDetails] = Field(..., description="Fare rules for inbound")


class FlightFareRulesResponse(BaseModel):
    """Flight fare rules response"""

    session_id: str = Field(..., description="Echo from request")
    fare_source_code: str = Field(..., description="Echo from request")
    baggage_information: list[BaggageInformation] = Field(
        ..., description="Baggage information"
    )
    fare_rules: list[FareRuleDetails] = Field(..., description="Fare rules")
    inbound_fare_data: InboundFareData | None = Field(
        None, description="Indian domestic roundtrips only"
    )
    errors: list[ErrorDetails] | None = Field(None, description="Error details if any")


# ======== 3. EXTRA SERVICES SCHEMAS ========


class FlightExtraServicesRequest(BaseModel):
    """Flight extra services request"""

    session_id: str = Field(..., description="Token from availability search")
    fare_source_code: str = Field(..., description="Unique fare identification code")


class BaseServiceOption(BaseModel):
    """Base class for service options"""

    service_id: str = Field(..., description="Unique ID for booking")
    check_in_location: CheckInLocation = Field(
        ..., description="Check-in location type"
    )
    service_description: ServiceDescription = Field(
        ..., description="Service description type"
    )
    pricing_description: str = Field(
        ...,
        description="Pricing description (e.g., 'The Baggage charges are added while making the ticket')",
    )
    is_mandatory_service: bool = Field(..., description="Mandatory service flag")
    minimum_quantity: int = Field(..., description="Minimum quantity")
    maximum_quantity: int = Field(..., description="Maximum quantity")
    service_pricing: MoneyAmount = Field(..., description="Service cost")


class BaggageServiceOption(BaseServiceOption):
    """Baggage service option"""

    pass


class MealServiceOption(BaseServiceOption):
    """Meal service option"""

    pass


class SeatOption(BaseModel):
    """Seat option"""

    service_id: str = Field(..., description="Unique seat ID")
    airline: AirlineInfo | None = Field(None, description="Airline details")
    flight_number: FlightNumber | None = Field(None, description="Flight details")


class SeatRow(BaseModel):
    """Seat row configuration"""

    row_number: str = Field(..., description="Row identifier")
    available_seats: list[SeatOption] = Field(..., description="Available seats in row")


class AircraftDeck(BaseModel):
    """Aircraft deck configuration"""

    deck_number: int = Field(..., description="Deck number")
    seat_rows: list[SeatRow] = Field(..., description="Seat row configuration")


class BaggageServiceCategory(BaseModel):
    """Baggage service category"""

    service_behavior: ServiceBehavior = Field(..., description="Service behavior type")
    allows_multi_select: bool = Field(
        ..., description="Can select multiple baggage items"
    )
    available_services: list[BaggageServiceOption] = Field(
        ..., description="Available baggage options"
    )


class MealServiceCategory(BaseModel):
    """Meal service category"""

    service_behavior: ServiceBehavior = Field(..., description="Service behavior type")
    allows_multi_select: bool = Field(..., description="Can select multiple meal items")
    available_services: list[MealServiceOption] = Field(
        ..., description="Available meal options"
    )


class SeatServiceCategory(BaseModel):
    """Seat service category"""

    aircraft_decks: list[AircraftDeck] = Field(
        ..., description="Aircraft deck configuration"
    )


class ExtraServicesData(BaseModel):
    """Extra services data"""

    baggage_services: list[BaggageServiceCategory] | None = Field(
        None, description="Baggage options per sector"
    )
    meal_services: list[MealServiceCategory] | None = Field(
        None, description="Meal options per sector"
    )
    seat_services: list[SeatServiceCategory] | None = Field(
        None, description="Seat selection options per segment"
    )


class FlightExtraServicesResponse(BaseModel):
    """Flight extra services response"""

    session_id: str = Field(..., description="Echo from request")
    fare_source_code: str = Field(..., description="Echo from request")
    is_successful: bool = Field(..., description="Success indicator")
    extra_services_data: ExtraServicesData = Field(
        ..., description="Available services"
    )
    errors: list[ErrorDetails] | None = Field(None, description="Error details if any")


# ======== 4. FARE REVALIDATION SCHEMAS ========


class FlightRevalidateRequest(BaseModel):
    """Flight revalidate request"""

    session_id: str = Field(..., description="Token from flight search response")
    fare_source_code: str = Field(
        ..., description="Unique fare ID from selected itinerary"
    )
    return_fare_source_code: str | None = Field(
        default=None,
        description="Inbound fare source for Indian domestic round trips only; omit for OneWay and Circle.",
    )
    adults: int | None = Field(
        default=None,
        description="Number of adult passengers (optional but recommended)",
    )
    children: int | None = Field(
        default=None, description="Number of child passengers (optional)"
    )
    infants: int | None = Field(
        default=None, description="Number of infant passengers (optional)"
    )


class ValidatedFareTotals(BaseModel):
    """Validated fare totals"""

    base_fare: MoneyAmount = Field(..., description="Base fare amount")
    total_tax: MoneyAmount = Field(..., description="Total taxes")
    total_fare: MoneyAmount = Field(..., description="Total price (with platform fee)")
    original_total_fare: MoneyAmount | None = Field(
        None,
        description="Original total fare before platform fee (for frontend calculation)",
    )
    platform_fee_percentage: float | None = Field(
        None,
        description="Platform fee percentage (e.g., 5.0 for 5%)",
    )


class UpdatedFarePricing(BaseModel):
    """Updated fare pricing after revalidation"""

    has_mixed_booking_classes: bool = Field(
        ..., description="Different booking classes for passengers"
    )
    updated_fare_source_code: str = Field(..., description="Updated fare code")
    fare_type: FareType = Field(..., description="Fare type")
    is_refundable: bool = Field(..., description="Refund policy")
    validated_fare_totals: ValidatedFareTotals = Field(
        ..., description="Price breakdown"
    )
    passenger_fare_breakdown: list[PassengerFareBreakdown] = Field(
        default_factory=list, description="Per passenger type fare breakdown"
    )


class ValidatedFareItinerary(BaseModel):
    """Validated fare itinerary"""

    sequence_number: str | None = Field(None, description="Sequence identifier")
    journey_type: JourneyType = Field(..., description="Journey type")
    requires_passport: bool = Field(..., description="Passport required for booking")
    requires_passport_issue_date: bool = Field(
        ..., description="Passport issue date required"
    )
    validating_airline: AirlineInfo = Field(..., description="Ticketing airline")
    required_booking_fields: list[RequiredBookingField] = Field(
        ..., description="Fields required for booking"
    )
    flight_legs: list[FlightLeg] = Field(..., description="Flight legs")
    updated_pricing: UpdatedFarePricing = Field(..., description="Pricing details")


class ServiceOption(BaseModel):
    """Service option for revalidation"""

    service_id: str = Field(..., description="Service identifier")
    service_type: ServiceType = Field(..., description="Service category")
    description: str = Field(..., description="Service description")
    cost: MoneyAmount = Field(..., description="Service cost")


class AvailableExtraServices(BaseModel):
    """Available extra services for revalidation"""

    service_options: list[ServiceOption] = Field(
        ..., description="Available extra services (empty if none)"
    )


class FlightRevalidateResponse(BaseModel):
    """Flight revalidate response"""

    session_id: str = Field(..., description="Echo from request")
    fare_source_code: str = Field(..., description="Echo from request")
    return_fare_source_code: str | None = Field(
        None, description="Echo from request if provided"
    )
    is_fare_available: bool = Field(
        ..., description="true = proceed with booking, false = stop"
    )
    validated_fare_itineraries: list[ValidatedFareItinerary] = Field(
        ..., description="Always array format"
    )
    available_extra_services: AvailableExtraServices | None = Field(
        None, description="Available services"
    )
    errors: list[ErrorDetails] | None = Field(None, description="Error details if any")


# ======== 5. BOOKING SCHEMAS ========


class SelectedExtraService(BaseModel):
    """Selected extra service for booking"""

    service_id: str = Field(..., description="Service ID from FlightLogic")
    service_quantity: int = Field(..., description="Quantity selected")
    segment_number: int = Field(..., description="Flight segment number (0-based)")
    service_cost: MoneyAmount = Field(..., description="Service cost")


class SeatSelection(BaseModel):
    """Seat selection for booking"""

    seat_service_id: str = Field(..., description="Seat service ID from FlightLogic")
    segment_number: int = Field(..., description="Flight segment number (0-based)")
    seat_description: str | None = Field(None, description="Human readable seat info")
    seat_cost: MoneyAmount | None = Field(None, description="Seat cost if applicable")


class FrequentFlyerInfo(BaseModel):
    """Frequent flyer information"""

    airline: AirlineInfo = Field(..., description="FF program airline")
    program_name: str = Field(..., description="Program name")
    member_number: str = Field(..., description="Member number")
    member_tier: FrequentFlyerTier | None = Field(None, description="Member tier level")


class PassengerServiceSelections(BaseModel):
    """Passenger service selections"""

    outbound_services: list[SelectedExtraService] | None = Field(
        None, description="Outbound services"
    )
    inbound_services: list[SelectedExtraService] | None = Field(
        None, description="Inbound services"
    )
    outbound_seat_selections: list[SeatSelection] | None = Field(
        None, description="Outbound seats"
    )
    inbound_seat_selections: list[SeatSelection] | None = Field(
        None, description="Inbound seats"
    )


class AdultPassenger(BaseModel):
    """Adult passenger information"""

    personal_info: PersonalInfo = Field(..., description="Basic personal details")
    travel_documents: TravelDocuments | None = Field(
        default=None, description="Passport and visa info"
    )
    saved_passenger_id: str | None = Field(
        default=None,
        description="Ref to stored passenger; backend fetches travel_documents from DB",
    )
    service_selections: PassengerServiceSelections | None = Field(
        default=None, description="Selected services"
    )
    frequent_flyer_info: FrequentFlyerInfo | None = Field(
        default=None, description="FF program details"
    )

    @model_validator(mode="after")
    def validate_adult_age(self) -> "AdultPassenger":
        """Validate that adult passenger is at least 12 years old (FlightLogic ADT = 12+)."""
        from .validators import PassengerValidator

        PassengerValidator.validate_adult_age(self.personal_info.date_of_birth)
        return self


class ChildPassenger(BaseModel):
    """Child passenger information"""

    personal_info: PersonalInfo = Field(..., description="Basic personal details")
    travel_documents: TravelDocuments | None = Field(
        default=None, description="Passport and visa info"
    )
    saved_passenger_id: str | None = Field(
        default=None,
        description="Ref to stored passenger; backend fetches travel_documents from DB",
    )
    service_selections: PassengerServiceSelections | None = Field(
        default=None, description="Selected services"
    )
    frequent_flyer_info: FrequentFlyerInfo | None = Field(
        default=None, description="FF program details"
    )

    @model_validator(mode="after")
    def validate_child_age(self) -> "ChildPassenger":
        """Validate that child passenger is between 2 and 11 years old."""
        from .validators import PassengerValidator

        PassengerValidator.validate_child_age_pydantic(self.personal_info.date_of_birth)
        return self


class InfantPassenger(BaseModel):
    """Infant passenger information"""

    personal_info: PersonalInfo = Field(..., description="Basic personal details")
    travel_documents: TravelDocuments | None = Field(
        default=None, description="Passport and visa info"
    )
    saved_passenger_id: str | None = Field(
        default=None,
        description="Ref to stored passenger; backend fetches travel_documents from DB",
    )
    service_selections: PassengerServiceSelections | None = Field(
        default=None, description="Selected services"
    )
    frequent_flyer_info: FrequentFlyerInfo | None = Field(
        default=None, description="FF program details"
    )

    @model_validator(mode="after")
    def validate_infant_age(self) -> "InfantPassenger":
        """Validate that infant passenger is under 2 years old."""
        from .validators import PassengerValidator

        PassengerValidator.validate_infant_age_pydantic(
            self.personal_info.date_of_birth
        )
        return self


class PassengerGroups(BaseModel):
    """Passenger groups"""

    adults: list[AdultPassenger] | None = Field(
        default=None, description="Required if adults > 0"
    )
    children: list[ChildPassenger] | None = Field(
        default=None, description="Required if children > 0"
    )
    infants: list[InfantPassenger] | None = Field(
        default=None, description="Required if infants > 0"
    )


class FlightBookingRequest(BaseFlightLogicRequest):
    """Flight booking request"""

    session_id: str = Field(..., description="Session token from availability search")
    fare_source_code: str = Field(..., description="Unique fare ID")
    requires_passport: bool = Field(..., description="Passport required for booking")
    fare_type: FareType = Field(..., description="Fare type")
    payment_id: str | None = Field(
        default=None,
        description="Payment ID - required for LCC bookings, optional for GDS",
    )
    inbound_fare_source_code: str | None = Field(
        default=None,
        description="Required for Indian domestic round trips only; omit for Circle (single priced itinerary).",
    )
    client_reference: str | None = Field(
        default=None, description="Unique booking reference"
    )
    postal_code: PostalCode | None = Field(default=None, description="Postal code")
    contact_information: ContactInformation = Field(..., description="Contact details")
    booking_notes: BookingNotes | None = Field(
        default=None, description="Structured booking notes"
    )
    passenger_groups: PassengerGroups = Field(
        ..., description="Structured passenger information"
    )
    required_fields: list[str] | None = Field(
        default=None,
        description="Required booking fields from revalidate response for validation",
    )
    cancellation_policy_text: str | None = Field(
        default=None,
        description="Cancellation policy text from fare rules (optional, for ticket email)",
    )
    saved_itinerary_id: str | None = Field(
        None,
        description="Optional saved itinerary id to link this booking after successful confirmation",
    )
    parent_voya_booking_reference: str | None = Field(
        default=None,
        description="Multicity group id (e.g. VOYA-MC-…) stored on each leg booking event",
    )
    multistay_leg_index: int | None = Field(
        default=None,
        description="Zero-based itinerary leg index for multi-stay/multicity (stored on booking event for ordering)",
    )
    voucher_redemption_id: str | None = Field(
        default=None,
        description="Discounts collection id from POST /vouchers/apply; requires client_reference matching reservation",
    )


class FlightBookingResponse(BaseModel):
    """Flight booking response"""

    booking_status: BookingStatus = Field(..., description="Booking status")
    is_successful: bool = Field(..., description="Success indicator")
    external_booking_reference: str = Field(
        ..., description="FlightLogic booking reference (UniqueID)"
    )
    voya_booking_reference: str | None = Field(
        None, description="VOYA user-facing booking reference"
    )
    airline_pnr: AirlinePNR | None = Field(
        None,
        description="Airline PNR (6-digit code) - may not be available immediately after booking",
    )
    ticket_time_limit: DateTime | None = Field(None, description="Ticket time limit")
    environment: FlightAPIEnvironment = Field(..., description="Environment type")
    errors: list[ErrorDetails] = Field(..., description="Error details if any")


class FlightMyBookingListItem(BaseModel):
    """Stable JSON item for GET /flights/my-bookings (profile and list UIs).

    Sourced from booking_events (FLIGHT). Amount is major currency units when stored.
    """

    voya_booking_reference: str | None = Field(
        None, description="VOYA-XXXXXXXXXX when assigned"
    )
    action: Literal["BOOKED", "CANCELLED", "PENDING"] = Field(
        ..., description="Event action from booking_events"
    )
    timestamp: datetime = Field(..., description="When the booking event was recorded")
    date_booked: datetime | None = Field(
        None, description="Supplier confirmation time when known (UTC)"
    )
    amount: float | None = Field(
        None, description="Total in major currency units when stored on the event"
    )
    departure_airport_iata: str | None = Field(
        None, description="Departure airport for summary display"
    )
    ticket_status: str | None = Field(
        None, description="Latest ticket status from trip details sync when present"
    )
    flight_leg_summaries: list[FlightLegSummary] | None = Field(
        None,
        description="Travel leg snapshots from trip_details (omit until synced or backfilled)",
    )
    flight_segment_departure_dates: list[str] | None = Field(
        None,
        description="UTC calendar departure date per segment (YYYY-MM-DD), trip_details order",
    )


# ======== 6. TICKETING SCHEMAS ========


class TicketOrderRequest(BaseFlightLogicRequest):
    """Ticket order request - uses VOYA booking reference.

    Frontend sends voya_booking_reference, backend converts to external reference internally.
    User ownership is validated automatically.
    """

    voya_booking_reference: str = Field(
        ..., description="VOYA internal booking reference (VOYA-XXXXXXXXXX)"
    )
    external_booking_reference: str | None = Field(
        None,
        description="External provider booking reference (auto-populated from VOYA reference)",
    )
    payment_id: str | None = Field(
        None, description="Payment ID - required for GDS ticket issuance"
    )
    cancellation_policy_text: str | None = Field(
        None, description="Cancellation policy text from fare rules (from localStorage)"
    )


class TicketOrderResponse(BaseModel):
    """Ticket order response"""

    success: bool = Field(..., description="Success indicator")
    external_booking_reference: str = Field(
        ..., description="FlightLogic booking reference (UniqueID)"
    )
    environment: FlightAPIEnvironment = Field(..., description="Environment type")
    errors: list[ErrorDetails] = Field(..., description="Error details if any")


# ======== 7. CANCELLATION SCHEMAS ========


class FlightCancelRequest(BaseFlightLogicRequest):
    """Flight cancel request - uses VOYA booking reference.

    Frontend sends voya_booking_reference, backend converts to external reference internally.
    User ownership is validated automatically.
    """

    voya_booking_reference: str = Field(
        ..., description="VOYA internal booking reference (VOYA-XXXXXXXXXX)"
    )
    external_booking_reference: str | None = Field(
        None,
        description="External provider booking reference (auto-populated from VOYA reference)",
    )


class FlightCancelResponse(BaseModel):
    """Flight cancel response"""

    success: bool = Field(..., description="Success indicator")
    external_booking_reference: str | None = Field(
        None, description="FlightLogic cancelled booking reference (UniqueID)"
    )
    errors: list[ErrorDetails] = Field(..., description="Error details")


# ======== 8. TRIP DETAILS SCHEMAS ========


class TripDetailsRequest(BaseFlightLogicRequest):
    """Trip details request - uses VOYA booking reference.

    Frontend sends voya_booking_reference, backend converts to external reference internally.
    User ownership is validated automatically.
    """

    voya_booking_reference: str | None = Field(
        None,
        description="VOYA internal booking reference (VOYA-XXXXXXXXXX)",
    )
    external_booking_reference: str | None = Field(
        default=None,
        description="External provider booking reference (auto-populated from VOYA reference)",
    )

    @model_validator(mode="after")
    def validate_at_least_one_reference(self) -> Self:
        if not self.voya_booking_reference and not self.external_booking_reference:
            msg = "Either voya_booking_reference or external_booking_reference is required"
            raise ValueError(msg)
        return self


class PassengerDetails(BaseModel):
    """Passenger details for trip details"""

    passenger_type: PassengerType = Field(..., description="Passenger type")
    personal_info: PersonalInfo = Field(..., description="Personal information")
    reference_id: int = Field(..., description="Passenger reference number")
    e_ticket_number: str | None = Field(None, description="E-ticket number")
    travel_documents: TravelDocuments | None = Field(
        None, description="Passport and visa info"
    )
    contact_info: ContactInformation | None = Field(None, description="Contact details")
    postal_code: PostalCode | None = Field(None, description="Postal code details")


class TripDetailsFlightSegment(BaseModel):
    """Trip details flight segment"""

    segment_id: int = Field(..., description="Segment number")
    departure_datetime: DateTime = Field(..., description="Departure date and time")
    arrival_datetime: DateTime = Field(..., description="Arrival date and time")
    departure_airport: AirportInfo = Field(..., description="Departure airport details")
    arrival_airport: AirportInfo = Field(..., description="Arrival airport details")
    departure_terminal: TerminalInfo | None = Field(
        None, description="Departure terminal details"
    )
    arrival_terminal: TerminalInfo | None = Field(
        None, description="Arrival terminal details"
    )
    marketing_flight_number: FlightNumber = Field(
        ..., description="Marketing flight details"
    )
    operating_airline: AirlineInfo = Field(..., description="Operating airline details")
    marketing_airline: AirlineInfo = Field(..., description="Marketing airline details")
    operating_flight_number: FlightNumber = Field(
        ..., description="Operating flight details"
    )
    aircraft: AircraftInfo | None = Field(None, description="Aircraft details")
    flight_duration: Duration = Field(..., description="Flight duration details")
    segment_stops: int = Field(..., description="Number of stops")
    passenger_count: int = Field(..., description="Total passengers for this segment")
    airline_pnr: AirlinePNR = Field(..., description="Airline PNR details")
    cabin_class: CabinClass = Field(..., description="Cabin class type")
    booking_class_code: BookingClassCode | None = Field(
        None, description="Booking class details"
    )
    baggage_allowance: BaggageAllowanceInfo | None = Field(
        None, description="Baggage allowance details"
    )
    e_ticket: bool = Field(..., description="E-ticket availability")
    meal_code: MealCode | None = Field(None, description="Meal preference")
    marriage_group: MarriageGroup | None = Field(None, description="Marriage indicator")
    seat_availability: SeatAvailability | None = Field(
        None, description="Seat availability info"
    )
    stop_details: list[StopDetail] | None = Field(
        None, description="Stop details if stops > 0"
    )


class PassengerCount(BaseModel):
    """Passenger count information"""

    type: PassengerType = Field(..., description="Passenger type")
    quantity: int = Field(..., description="Number of passengers of this type")


class PassengerFare(BaseModel):
    """Passenger fare breakdown"""

    base_fare: MoneyAmount = Field(..., description="Base fare per passenger")
    service_tax: MoneyAmount = Field(..., description="Service tax per passenger")
    total_tax: MoneyAmount = Field(..., description="Total tax per passenger")
    total_fare: MoneyAmount = Field(..., description="Total per passenger")


class FareBreakdown(BaseModel):
    """Fare breakdown per passenger type"""

    passenger_type_info: PassengerTypeInfo = Field(
        ..., description="Passenger type info"
    )
    individual_fare: IndividualPassengerFare = Field(
        ..., description="Per-passenger fare"
    )
    baggage_allowance: list[BaggageAllowance] = Field(
        default_factory=list, description="Baggage allowance"
    )
    cabin_baggage_allowance: list[CabinBaggageAllowance] = Field(
        default_factory=list, description="Cabin baggage"
    )
    fare_basis_codes: list[str] = Field(
        default_factory=list, description="Fare basis codes"
    )
    penalty_details: PenaltyDetails | None = Field(
        None, description="Penalty information"
    )


class ExtraService(BaseModel):
    """Extra service for trip details"""

    passenger_reference_id: int = Field(..., description="Passenger reference")
    service_id: str = Field(..., description="Service identifier")
    service_type: ServiceType = Field(..., description="Service category")
    description: str = Field(..., description="Service description")
    behavior: ServiceBehavior = Field(..., description="Service behavior pattern")
    check_in_type: CheckInLocation = Field(..., description="Check-in location")
    is_mandatory: bool = Field(..., description="Service requirement flag")
    cost: MoneyAmount = Field(..., description="Service pricing")


class TripDetailsResponse(BaseModel):
    """Trip details response"""

    success: bool = Field(..., description="Success indicator")
    voya_booking_reference: str | None = Field(
        None, description="VOYA user-facing booking reference (VOYA-XXXXXXXXXX)"
    )
    booking_status: BookingStatus = Field(..., description="Current booking status")
    cross_border_indicator: bool = Field(
        ..., description="International flight indicator"
    )
    destination: AirportInfo = Field(..., description="Destination airport details")
    origin: AirportInfo = Field(..., description="Origin airport details")
    fare_type: FareType = Field(..., description="Fare type")
    is_commissionable: bool = Field(..., description="Commission eligibility")
    is_mo_fare: bool = Field(..., description="Markup fare indicator")
    external_booking_reference: str = Field(
        ..., description="FlightLogic booking reference (UniqueID)"
    )
    ticket_status: TicketStatus = Field(..., description="Current ticket status")
    environment: FlightAPIEnvironment = Field(..., description="Environment type")
    passengers: list[PassengerDetails] = Field(
        ..., description="Passenger information array"
    )
    segments: list[TripDetailsFlightSegment] = Field(
        ..., description="Flight segments array"
    )
    pricing: FarePricing = Field(..., description="Total pricing information")
    fare_breakdown: list[FareBreakdown] = Field(
        ..., description="Per-passenger pricing"
    )
    extra_services: list[ExtraService] = Field(
        ..., description="Available additional services"
    )
    booking_notes: list[BookingNote] = Field(..., description="Booking notes array")
    errors: list[ErrorDetails] = Field(..., description="Error details if any")
    parent_voya_booking_reference: str | None = Field(
        default=None,
        description="Multicity group id from Mongo when this VOYA ref is one leg of a group",
    )


# ============================================================
# AIRPORT LIST SCHEMAS
# ============================================================


class AirportListRequest(BaseFlightLogicRequest):
    """Request schema for getting airport list from FlightLogic."""

    pass  # No additional fields needed, inherits from BaseFlightLogicRequest


class AirportListItem(BaseModel):
    """Single airport item in airport list response."""

    iata_code: str = Field(..., description="3-letter IATA airport code")
    airport_name: str = Field(..., description="Full airport name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    latitude: float | None = Field(None, description="Latitude coordinate (optional)")
    longitude: float | None = Field(None, description="Longitude coordinate (optional)")


class AirportListResponse(BaseModel):
    """Response schema for airport list from FlightLogic."""

    airports: list[AirportListItem] = Field(
        ..., description="List of commercial airports (excluding private/military)"
    )
    errors: list[ErrorDetails] = Field(
        default_factory=list, description="Error details if any"
    )


# ============================================================
# AIRLINE LIST SCHEMAS
# ============================================================


class AirlineListRequest(BaseFlightLogicRequest):
    """Request schema for getting airline list from FlightLogic."""

    pass  # No additional fields needed, inherits from BaseFlightLogicRequest


class AirlineListItem(BaseModel):
    """Single airline item in airline list response."""

    iata_code: str = Field(..., description="2-letter IATA airline code")
    name: str = Field(..., description="Full airline name")
    logo_url: str = Field(..., description="URL to airline logo")


class AirlineListResponse(BaseModel):
    """Response schema for airline list from FlightLogic."""

    airlines: list[AirlineListItem] = Field(
        ..., description="List of airlines with codes, names, and logo URLs"
    )
