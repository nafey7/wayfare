"""FlightLogic API Data Transfer Objects (DTOs).

These models match the FlightLogic API structure.
They should only be used within the FlightLogic integration.
Convert to domain models before returning to the application.

Note: mixedCase field names are required to match FlightLogic API format.
"""
# ruff: noqa: N815

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, RootModel, field_validator

# ============================================================
# SEARCH DTOs - Nested structures
# ============================================================


class OriginDestinationInfo(BaseModel):
    """Origin and destination information for flight search."""

    model_config = {"exclude_none": True}  # Exclude None values from JSON

    departureDate: str  # Format: YYYY-MM-DD
    returnDate: str | None = None  # For Return journeyType only, Format: YYYY-MM-DD
    airportOriginCode: str  # 3-letter IATA code
    airportDestinationCode: str  # 3-letter IATA code


class FlightLogicSearchRequest(BaseModel):
    """FlightLogic API search request format - matches documentation exactly."""

    user_id: str
    user_password: str
    access: Literal["Test", "Production"]
    ip_address: str
    requiredCurrency: str = "USD"  # 3-character ISO currency code
    journeyType: Literal["OneWay", "Return", "Circle"]
    OriginDestinationInfo: list[OriginDestinationInfo]
    class_: Literal["Economy", "Business", "First", "PremiumEconomy"] = Field(
        ..., alias="class"
    )
    adults: int
    children: int = Field(
        ..., alias="childs"
    )  # API expects "childs" not "children" - required field with alias
    infants: int = 0
    airlineCode: str | None = None  # Two letter airline code
    directFlight: Literal[0, 1] | None = None  # 0 = all flights, 1 = direct only
    city_wise_search_origin: bool = True  # Search all airports in origin city
    city_wise_search_destination: bool = True  # Search all airports in destination city


# Search Response structures
class AmountInfo(BaseModel):
    """Amount information in responses."""

    Amount: str
    CurrencyCode: str
    DecimalPlaces: str | int


class OperatingAirline(BaseModel):
    """Operating airline information."""

    Code: str  # Airline code e.g., "6E"
    Name: str | None = None  # Airline name e.g., "Indigo Airlines"
    Equipment: str  # Aircraft equipment number e.g., "320"
    FlightNumber: str  # Operating flight number


class FlightSegment(BaseModel):
    """Flight segment details."""

    ArrivalAirportLocationCode: str
    ArrivalDateTime: str  # Format: 2023-02-19T10:56:00
    CabinClassCode: str  # Y-Economy, S-Premium Economy, C-Business, F-First
    CabinClassText: str | None = None  # For LCC/WebFares only
    DepartureAirportLocationCode: str
    DepartureDateTime: str
    Eticket: bool
    JourneyDuration: int  # In minutes
    FlightNumber: str
    MarketingAirlineCode: str
    MarketingAirlineName: str | None = None  # e.g., "Indigo Airlines"
    MarriageGroup: str | None = None  # Marriage group indicator
    MealCode: str | None = None  # Meal preference code
    OperatingAirline: OperatingAirline


class SeatsRemaining(BaseModel):
    """Seats remaining information."""

    BelowMinimum: bool  # True if seats <= 0
    Number: int  # Number of seats remaining


class StopQuantityInfo(BaseModel):
    """Stop information."""

    ArrivalDateTime: str = ""  # Empty string if no stop
    DepartureDateTime: str = ""
    Duration: str = ""
    LocationCode: str = ""  # Airport code of stop


class OriginDestinationOption(BaseModel):
    """Single origin-destination option."""

    FlightSegment: FlightSegment
    ResBookDesigCode: str = (
        ""  # RBD - Reservation Booking Designator (e.g., "Y", "B", "M" for economy)
    )
    ResBookDesigText: str = (
        ""  # For LCC fares only (e.g., "Lowest Fare", "Flex", "Premium")
    )
    SeatsRemaining: SeatsRemaining
    StopQuantity: int  # Number of stops
    StopQuantityInfo: Optional[StopQuantityInfo] = None

    @field_validator("ResBookDesigCode")
    @classmethod
    def validate_rbd_code(cls, value: str) -> str:
        """Validate RBD code for GDS bookings."""
        if not value:
            return ""  # Empty for LCC/WebFare bookings

        # RBD must be single uppercase letter (airline-specific)
        if len(value) != 1 or not value.isupper():
            raise ValueError(
                f"Invalid RBD code: {value}. Must be single uppercase letter"
            )

        return value


class OriginDestinationOptions(BaseModel):
    """Container for origin-destination options."""

    OriginDestinationOption: list[OriginDestinationOption]
    TotalStops: int


class PassengerTypeQuantity(BaseModel):
    """Passenger type and quantity."""

    Code: Literal["ADT", "CHD", "INF"]  # Adult, Child, Infant
    Quantity: int


class Tax(BaseModel):
    """Tax details."""

    TaxCode: str
    Amount: str
    CurrencyCode: str
    DecimalPlaces: str


class PassengerFare(BaseModel):
    """Passenger fare breakdown."""

    BaseFare: AmountInfo
    EquivFare: AmountInfo | None = None
    ServiceTax: AmountInfo | None = None
    Surcharges: AmountInfo | None = None
    Taxes: list[Tax] | None = None
    TotalFare: AmountInfo


class PenaltyDetails(BaseModel):
    """Penalty details for changes/refunds."""

    Currency: str
    RefundAllowed: bool
    RefundPenaltyAmount: str
    ChangeAllowed: bool
    ChangePenaltyAmount: str


class FareBreakdown(BaseModel):
    """Fare breakdown per passenger type."""

    FareBasisCode: list[str] | None = None
    Baggage: list[str]  # Per segment
    CabinBaggage: list[str]  # Per segment
    PassengerFare: PassengerFare
    PassengerTypeQuantity: PassengerTypeQuantity
    PenaltyDetails: list[PenaltyDetails] | None = None


class ItinTotalFares(BaseModel):
    """Total fare information."""

    BaseFare: AmountInfo
    EquivFare: AmountInfo | None = None
    ServiceTax: AmountInfo | None = None
    TotalTax: AmountInfo
    TotalFare: AmountInfo


class AirItineraryFareInfo(BaseModel):
    """Air itinerary fare information."""

    DivideInPartyIndicator: bool
    FareSourceCode: str
    FareInfos: list[Any] | None = None
    FareType: Literal["Private", "Public", "WebFare"]
    ResultIndex: str | None = None
    IsRefundable: bool
    ItinTotalFares: ItinTotalFares
    FareBreakdown: list[FareBreakdown]
    SplitItinerary: bool | None = None


class FareItinerary(BaseModel):
    """Complete fare itinerary."""

    DirectionInd: Literal["OneWay", "Return", "Circle"]
    AirItineraryFareInfo: AirItineraryFareInfo
    OriginDestinationOptions: list[OriginDestinationOptions]
    IsPassportMandatory: str | bool | None = (
        None  # "true"/"false" string or boolean - passport required for booking
    )
    IsPassportFullDetailsMandatory: bool | None = (
        None  # From revalidate - full passport details required
    )
    SequenceNumber: str | None = None
    TicketType: str | None = None  # e.g., "eTicket"
    ValidatingAirlineCode: str
    RequiredFieldsToBook: list[str] | None = None  # From revalidate response

    @field_validator("IsPassportMandatory")
    @classmethod
    def normalize_passport_mandatory(cls, value: str | bool | None) -> bool:
        """Normalize passport mandatory field to boolean."""
        if value is None:
            return False

        # Handle string boolean values
        if isinstance(value, str):
            return value.lower() == "true"

        return bool(value)


class FareItineraries(BaseModel):
    """Container for fare itineraries."""

    FareItinerary: FareItinerary | list[FareItinerary]


class AirSearchResult(BaseModel):
    """Air search result container."""

    FareItineraries: list[dict[str, Any]] | None = (
        None  # Contains FareItinerary structures
    )


class AirSearchResponseData(BaseModel):
    """Air search response data.

    For Indian domestic round trip searches:
    - Outbound itinerary: AirSearchResult
    - Inbound itinerary: AirSearchResultInbound (separate structure)
    """

    session_id: str
    supplier: str | None = None  # Not always present in response
    AirSearchResult: AirSearchResult  # Outbound flights (or all flights for OneWay)
    AirSearchResultInbound: AirSearchResult | None = (
        None  # Inbound flights for Indian domestic round trips
    )


class FlightLogicSearchResponse(BaseModel):
    """FlightLogic API search response format - matches documentation exactly."""

    AirSearchResponse: AirSearchResponseData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# REVALIDATION DTOs
# ============================================================


class FlightLogicRevalidateRequest(BaseModel):
    """FlightLogic API revalidate request format - matches documentation exactly."""

    session_id: str  # From search response
    fare_source_code: str  # From search response
    fare_source_code_inbound: str | None = None  # For Indian Domestic RoundTrip


class AirRevalidateResult(BaseModel):
    """Air revalidate result."""

    IsValid: bool | str  # Can be boolean or "false" as string
    FareItineraries: dict[str, Any] | None = None
    ExtraServices: dict[str, Any] | None = None
    RequiredFieldsToBook: list[str] | None = None  # Critical for booking validation
    IsPassportFullDetailsMandatory: bool | None = (
        None  # Critical for passport requirements
    )
    SequenceNumber: str | None = None

    @field_validator("FareItineraries", mode="before")
    @classmethod
    def normalize_fare_itineraries(cls, value: Any) -> dict[str, Any] | None:
        """Convert empty list to None for FareItineraries (happens when fare unavailable)."""
        if isinstance(value, list) and len(value) == 0:
            return None
        return value


class AirRevalidateResponseData(BaseModel):
    """Air revalidate response data."""

    AirRevalidateResult: AirRevalidateResult
    AirRevalidateResultInbound: AirRevalidateResult | None = None  # For Indian domestic


class FlightLogicRevalidateResponse(BaseModel):
    """FlightLogic API revalidate response format - matches documentation exactly."""

    AirRevalidateResponse: AirRevalidateResponseData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# BOOKING DTOs - Nested structures
# ============================================================


class ExtraServiceItem(BaseModel):
    """Extra service item for booking."""

    serviceId: str
    quantity: str
    segment: str  # Segment number starting from 0


class AdultPassenger(BaseModel):
    """Adult passenger details for booking.

    FlightLogic expects arrays for all fields to support multiple adults in one object.
    Each array index represents one adult passenger.
    """

    title: list[str]  # ["Mr", "Mrs"] - one per adult
    firstName: list[str]  # ["John", "Jane"]
    lastName: list[str]  # ["Smith", "Smith"]
    dob: list[str]  # ["1985-03-15", "1987-07-22"] - Format: YYYY-MM-DD
    nationality: list[str]  # ["US", "US"] - Alpha-2 country codes
    passportNo: list[str] | None = None  # ["P12345678", "P87654321"]
    passportIssueCountry: list[str] | None = None  # ["US", "US"]
    passportExpiryDate: list[str] | None = None  # ["2030-12-31", "2030-06-15"]
    passportIssueDate: list[str] | None = (
        None  # Required if IsPassportFullDetailsMandatory
    )
    ExtraServiceOutbound: list[list[str]] | None = None  # [["19", "10"], ["19", "10"]]
    ExtraServiceInbound: list[list[str]] | None = None  # [["33"], ["33"]]
    ExtraServiceOutbound_1: list[list[ExtraServiceItem]] | None = None
    ExtraServiceInbound_1: list[list[ExtraServiceItem]] | None = None
    SeatOutbound: list[list[str]] | None = None  # Seat IDs per segment per passenger
    SeatInbound: list[list[str]] | None = None
    frequentFlyrNum: list[str] | None = None  # ["ABC123", None]


class ChildPassenger(BaseModel):
    """Child passenger details for booking.

    FlightLogic expects arrays for all fields to support multiple children in one object.
    Each array index represents one child passenger.
    """

    title: list[str]  # ["Master", "Miss"] - one per child
    firstName: list[str]  # ["Tom", "Sarah"]
    lastName: list[str]  # ["Smith", "Smith"]
    dob: list[str]  # ["2017-05-10", "2018-03-15"] - Format: YYYY-MM-DD
    nationality: list[str]  # ["US", "US"] - Alpha-2 country codes
    passportNo: list[str] | None = None  # ["P99887766", "P11223344"]
    passportIssueCountry: list[str] | None = None  # ["US", "US"]
    passportExpiryDate: list[str] | None = None  # ["2028-12-31", "2029-01-15"]
    passportIssueDate: list[str] | None = None
    ExtraServiceOutbound: list[list[str]] | None = None  # [["2", "32"], ["5"]]
    ExtraServiceInbound: list[list[str]] | None = None  # [["3", "46"], ["7"]]
    frequentFlyrNum: list[str] | None = None  # ["XYZ789", None]


class InfantPassenger(BaseModel):
    """Infant passenger details for booking.

    FlightLogic expects arrays for all fields to support multiple infants in one object.
    Each array index represents one infant passenger.
    """

    title: list[str]  # ["Master", "Miss"] - one per infant
    firstName: list[str]  # ["Baby", "Emma"]
    lastName: list[str]  # ["Smith", "Smith"]
    dob: list[str]  # ["2024-03-15", "2024-06-20"] - Format: YYYY-MM-DD
    nationality: list[str]  # ["US", "US"] - Alpha-2 country codes
    passportNo: list[str] | None = None  # ["P33445566", "P77889900"]
    passportIssueCountry: list[str] | None = None  # ["US", "US"]
    passportExpiryDate: list[str] | None = None  # ["2028-01-15", "2028-07-20"]
    passportIssueDate: list[str] | None = None
    frequentFlyrNum: list[str] | None = None  # Infants typically don't have FF numbers


class PaxDetails(BaseModel):
    """Passenger details container."""

    adult: AdultPassenger | None = None
    child: ChildPassenger | None = None
    infant: InfantPassenger | None = None


class FlightBookingInfo(BaseModel):
    """Flight booking information."""

    flight_session_id: str
    fare_source_code: str
    IsPassportMandatory: str  # "true" or "false" as string
    fareType: Literal["Private", "Public", "WebFare"]
    payment_id: str | None = None  # Payment ID - required for LCC, optional for GDS
    areaCode: str
    countryCode: str | None = None
    fare_source_code_inbound: str | None = None  # For Indian Domestic RoundTrip


class PaxInfo(BaseModel):
    """Passenger and contact information for booking."""

    clientRef: str | None = None
    postCode: str | None = None
    customerEmail: str
    customerPhone: str
    bookingNote: str | None = None
    paxDetails: list[PaxDetails]


class FlightLogicBookingRequest(BaseModel):
    """FlightLogic API booking request format - matches documentation exactly."""

    flightBookingInfo: FlightBookingInfo
    paxInfo: PaxInfo


class BookFlightResult(BaseModel):
    """Book flight result."""

    Errors: Any | None = None  # Can be empty string or error structure
    Status: Literal["CONFIRMED", "PENDING", ""] | str
    Success: bool | str  # Can be boolean or "true"/"false" string
    Target: Literal["Test", "Production"]
    TktTimeLimit: str | None = None  # DateTime format
    UniqueID: str | None = None  # Booking reference


class BookFlightResponseData(BaseModel):
    """Book flight response data."""

    BookFlightResult: BookFlightResult


class FlightLogicBookingResponse(BaseModel):
    """FlightLogic API booking response format - matches documentation exactly."""

    BookFlightResponse: BookFlightResponseData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# TICKETING DTOs
# ============================================================


class FlightLogicTicketRequest(BaseModel):
    """FlightLogic API ticket request format - matches documentation exactly."""

    user_id: str
    user_password: str
    access: str
    ip_address: str
    UniqueID: str  # Booking reference from booking response


class TicketOrderResult(BaseModel):
    """Ticket order result."""

    Errors: Any | None = None  # Can be empty string or error structure
    Success: str  # "true" or "false" as string
    UniqueID: str
    Target: Literal["Test", "Production"]


class AirOrderTicketRSData(BaseModel):
    """Ticket order response data."""

    TicketOrderResult: TicketOrderResult


class FlightLogicTicketResponse(BaseModel):
    """FlightLogic API ticket response format - matches documentation exactly."""

    AirOrderTicketRS: AirOrderTicketRSData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# CANCELLATION DTOs
# ============================================================


class FlightLogicCancelRequest(BaseModel):
    """FlightLogic API cancel request format - matches documentation exactly."""

    user_id: str
    user_password: str
    access: str
    ip_address: str
    UniqueID: str  # Booking reference to cancel


class CancelBookingResult(BaseModel):
    """Cancel booking result."""

    Errors: Any | None = None  # Can be empty string or error structure
    Success: str  # "true" or "false" as string
    Target: Literal["Test", "Production"]
    UniqueID: str | None = None


class CancelBookingResponseData(BaseModel):
    """Cancel booking response data."""

    CancelBookingResult: CancelBookingResult


class FlightLogicCancelResponse(BaseModel):
    """FlightLogic API cancel response format - matches documentation exactly."""

    CancelBookingResponse: CancelBookingResponseData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# EXTRA SERVICES DTOs
# ============================================================


class FlightLogicExtraServicesRequest(BaseModel):
    """FlightLogic API extra services request format - matches documentation exactly."""

    session_id: str  # From search response
    fare_source_code: str  # From search response


# Extra Services Response structures
class ServiceCost(BaseModel):
    """Service cost information."""

    Amount: str
    CurrencyCode: str
    DecimalPlaces: str


class ExtraService(BaseModel):
    """Individual extra service details."""

    ServiceId: str
    CheckInType: str  # e.g., "AIRPORT"
    Description: str
    FareDescription: str
    IsMandatory: bool
    MinimumQuantity: int
    MaximumQuantity: int
    ServiceCost: ServiceCost


class DynamicService(BaseModel):
    """Dynamic service (baggage/meal) container."""

    Behavior: Literal[
        "PER_PAX",
        "PER_PAX_OUTBOUND",
        "PER_PAX_INBOUND",
        "PER_PAX_SEGMENT",
        "PER_PAX_SEGMENT_OUTBOUND",
        "PER_PAX_SEGMENT_INBOUND",
        "GROUP_PAX",
        "GROUP_PAX_OUTBOUND",
        "GROUP_PAX_INBOUND",
    ]
    IsMultiSelect: bool
    Services: list[ExtraService]


class ExtraServicesData(BaseModel):
    """Extra services data container."""

    DynamicBaggage: list[DynamicService] | None = None
    DynamicMeal: list[DynamicService] | None = None
    DynamicSeat: list[dict[str, Any]] | None = None  # Complex seat structure


class ExtraServicesResult(BaseModel):
    """Extra services result."""

    success: bool
    ExtraServicesData: Optional[ExtraServicesData] = None


class ExtraServicesResponseData(BaseModel):
    """Extra services response data."""

    ExtraServicesResult: ExtraServicesResult


class FlightLogicExtraServicesResponse(BaseModel):
    """FlightLogic API extra services response format - matches documentation exactly."""

    ExtraServicesResponse: ExtraServicesResponseData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# FARE RULES DTOs
# ============================================================


class FlightLogicFareRulesRequest(BaseModel):
    """FlightLogic API fare rules request format - matches documentation exactly."""

    session_id: str  # From search response
    fare_source_code: str  # From search response
    fare_source_code_inbound: str | None = None  # For Indian Domestic RoundTrip


# Fare Rules Response structures
class BaggageInfo(BaseModel):
    """Baggage information."""

    Arrival: str  # 3-letter IATA code
    Baggage: str  # e.g., "1P", "30K", "SB" (Piece/Kilogram/Standard Baggage)
    Departure: str  # 3-letter IATA code
    FlightNo: str  # Operating flight number


class FareRule(BaseModel):
    """Fare rule details."""

    Airline: str  # Operating airline code
    CityPair: str  # e.g., "DELBOM"
    Category: str | None = None  # Rule category
    Rules: str | None = None  # Detailed rule description


class FareRules1_1Result(BaseModel):
    """Fare rules result."""

    BaggageInfos: list[dict[str, BaggageInfo]] | None = None
    FareRules: list[dict[str, FareRule]] | None = None


class FareRules1_1ResponseData(BaseModel):
    """Fare rules response data."""

    FareRules1_1Result: FareRules1_1Result
    FareRules1_1ResultInbound: FareRules1_1Result | None = None  # For Indian domestic


class FlightLogicFareRulesResponse(BaseModel):
    """FlightLogic API fare rules response format - matches documentation exactly."""

    FareRules1_1Response: FareRules1_1ResponseData | None = None
    Errors: FlightLogicError | None = None


# ============================================================
# TRIP DETAILS DTOs
# ============================================================


class FlightLogicTripDetailsRequest(BaseModel):
    """FlightLogic API trip details request format."""

    user_id: str
    user_password: str
    access: str
    ip_address: str
    UniqueID: str  # Booking reference ID


class TripDetailsPassenger(BaseModel):
    """Passenger details in trip details response."""

    Title: str
    FirstName: str
    LastName: str
    PassengerType: Literal["ADT", "CHD", "INF"]
    DateOfBirth: str | None = None
    Nationality: str | None = None
    PassportNumber: str | None = None
    PassportExpiryDate: str | None = None
    PassportIssuingCountry: str | None = None
    Email: str | None = None
    Phone: str | None = None
    eTicketNumber: str | None = (
        None  # FlightLogic API uses "eTicketNumber" not "TicketNumber"
    )
    SeatNumber: str | None = None


class TripDetailsSegment(BaseModel):
    """Flight segment in trip details response."""

    # Support both field naming conventions
    DepartureAirportCode: str | None = None
    DepartureAirportLocationCode: str | None = None  # Alternative name
    ArrivalAirportCode: str | None = None
    ArrivalAirportLocationCode: str | None = None  # Alternative name
    DepartureDateTime: str
    ArrivalDateTime: str
    FlightNumber: str
    MarketingAirlineCode: str
    OperatingAirlineCode: str | None = None
    OperatingFlightNumber: str | None = None
    AircraftType: str | None = None
    CabinClass: str | None = None
    BookingClass: str | None = None
    Duration: int | None = None  # In minutes
    Terminal: str | None = None
    AirlinePNR: str | None = None
    Status: str | None = None


class TripDetailsFare(BaseModel):
    """Fare details in trip details response."""

    BaseFare: AmountInfo
    Tax: AmountInfo | None = None
    TotalFare: AmountInfo
    FareBreakdown: list[FareBreakdown] | None = None


class TripDetailsBooking(BaseModel):
    """Booking details structure."""

    BookingReference: str | None = None
    UniqueID: str | None = None
    PNR: str | None = None
    Status: str | None = None
    BookingDate: str | None = None
    TicketTimeLimit: str | None = None
    Origin: str | dict[str, Any] | None = None
    Destination: str | dict[str, Any] | None = None
    JourneyType: str | None = None
    FareType: str | None = None
    IsRefundable: bool | None = None
    Passengers: list[TripDetailsPassenger] | None = None
    FlightSegments: list[TripDetailsSegment] | None = None
    Segments: list[TripDetailsSegment] | None = None  # Alternative field name
    FareDetails: TripDetailsFare | None = None
    TotalAmount: str | None = None
    Currency: str | None = None
    PaymentStatus: str | None = None
    TicketStatus: str | None = None
    ExtraServices: list[dict[str, Any]] | None = None
    BookingNotes: str | None = None
    CrossBorderIndicator: bool | None = None
    Environment: str | None = None


class FlightLogicTripDetailsResponse(BaseModel):
    """FlightLogic API trip details response format."""

    # Multiple possible response structures based on FlightLogic API versions
    TripDetailsResult: TripDetailsBooking | dict[str, Any] | None = None
    BookingDetails: TripDetailsBooking | None = None
    GetBookingDetailsResponse: dict[str, Any] | None = None
    TripDetails: TripDetailsBooking | None = None
    Success: bool | str | None = None
    Errors: FlightLogicError | None = None

    # Allow any additional fields from the actual API response
    model_config = {"extra": "allow"}


# ============================================================
# ERROR RESPONSE DTOs
# ============================================================


class FlightLogicError(BaseModel):
    """FlightLogic error structure."""

    ErrorCode: str
    ErrorMessage: str


class FlightLogicErrorResponse(BaseModel):
    """FlightLogic API error response format - matches documentation exactly."""

    Errors: FlightLogicError | None = None


# ============================================================
# AIRPORT LIST DTOs
# ============================================================


class FlightLogicAirportListRequest(BaseModel):
    """FlightLogic API airport list request format."""

    user_id: str
    user_password: str
    access: Literal["Test", "Production"]
    ip_address: str


class AirportListItemDTO(BaseModel):
    """Single airport item in airport list response from FlightLogic."""

    AirportCode: str  # IATA code (e.g., "AAA")
    AirportName: str  # Full airport name (e.g., "Anaa Airport")
    City: str  # City name (e.g., "Anaa")
    Country: str  # Country name (e.g., "French Polynesia")


class FlightLogicAirportListResponse(
    RootModel[list[AirportListItemDTO] | dict[str, Any] | None]
):
    """FlightLogic API airport list response format.

    Can be either:
    - List of AirportListItemDTO (success)
    - Error response with Errors field
    """

    root: list[AirportListItemDTO] | dict[str, Any] | None = None

    @property
    def airports(self) -> list[AirportListItemDTO]:
        """Get airports list, handling both list and dict responses."""
        if isinstance(self.root, list):
            return self.root
        return []

    @property
    def errors(self) -> FlightLogicError | None:
        """Get errors if present."""
        if isinstance(self.root, dict) and "Errors" in self.root:
            errors_data = self.root["Errors"]
            if isinstance(errors_data, dict):
                return FlightLogicError(**errors_data)
        return None


# ============================================================
# AIRLINE LIST DTOs
# ============================================================


class FlightLogicAirlineListRequest(BaseModel):
    """FlightLogic API airline list request format."""

    user_id: str
    user_password: str
    access: Literal["Test", "Production"]
    ip_address: str


class AirlineListItemDTO(BaseModel):
    """Single airline item in airline list response from FlightLogic."""

    AirLineCode: str  # IATA code (e.g., "BA", "00")
    AirLineName: str  # Airline name (e.g., "British Airways", "Janet")
    AirLineLogo: str  # Logo URL (e.g., "https://travelnext.works/api/airlines/BA.gif")
