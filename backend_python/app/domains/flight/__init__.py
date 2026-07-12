"""Flight domain package.

Clean domain-driven design for flight operations.
"""

from typing import TYPE_CHECKING

# Domain Enums
from app.domains.common import TravelTitle

from .enums import (
    BaggageUnit,
    BookingStatus,
    CabinClass,
    CarrierType,
    FareType,
    JourneyType,
    LCCBookingClass,
    PassengerType,
    PassportRequirement,
    TicketType,
)

# Events and Exceptions
from .events import FlightEventHandler
from .exceptions import (
    FlightApiError,
    FlightBookingError,
    FlightBookingSupplierSyncError,
    FlightDomainError,
    FlightSearchError,
    FlightValidationError,
)

# Schemas (Data Models)
from .schemas import (
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
    FlightMyBookingListItem,
    FlightRevalidateRequest,
    FlightRevalidateResponse,
    FlightSearchRequest,
    FlightSearchResponse,
    FlightSegment,
    MulticityLegSearchResult,
    TicketOrderRequest,
    TicketOrderResponse,
    TripDetailsRequest,
    TripDetailsResponse,
)

# Validators
from .validators import (
    MissingRequiredFieldError,
    validate_age_requirements,
    validate_passenger_counts,
    validate_required_fields_to_book,
)

__all__ = [  # noqa: RUF022 — grouped by domain (enums, exceptions, schemas, …)
    # Domain Enums
    "AirportListRequest",
    "AirportListResponse",
    "BaggageUnit",
    "BookingStatus",
    "CabinClass",
    "CarrierType",
    "FareType",
    "FlightApiError",
    "FlightBookingError",
    "FlightBookingSupplierSyncError",
    # Schemas
    "FlightBookingRequest",
    "FlightBookingResponse",
    "FlightCancelRequest",
    "FlightCancelResponse",
    "FlightDomainError",
    # Events and Exceptions
    "FlightEventHandler",
    "FlightExtraServicesRequest",
    "FlightExtraServicesResponse",
    "FlightFareRulesRequest",
    "FlightFareRulesResponse",
    "FlightMyBookingListItem",
    "FlightRevalidateRequest",
    "FlightRevalidateResponse",
    "FlightSearchError",
    "FlightSearchRequest",
    "FlightSearchResponse",
    "FlightSegment",
    "FlightValidationError",
    "JourneyType",
    "LCCBookingClass",
    # Validators
    "MissingRequiredFieldError",
    "MulticityLegSearchResult",
    "PassengerType",
    "PassportRequirement",
    "TicketOrderRequest",
    "TicketOrderResponse",
    "TicketType",
    "TravelTitle",
    "TripDetailsRequest",
    "TripDetailsResponse",
    "validate_age_requirements",
    "validate_passenger_counts",
    "validate_required_fields_to_book",
]

# FlightService NOT imported here - used via dependency injection
# Import directly from app.domains.flight.service where needed
