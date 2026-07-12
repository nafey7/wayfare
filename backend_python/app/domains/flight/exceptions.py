"""Flight domain exceptions.

All custom exceptions for flight operations with proper error handling.
"""


class FlightDomainError(Exception):
    """Base exception for all flight domain errors."""

    def __init__(
        self, message: str = "Flight domain error occurred", code: str | None = None
    ) -> None:
        self.message = message
        self.code = code or "FLIGHT_ERROR"
        super().__init__(self.message)


class FlightSearchError(FlightDomainError):
    """Raised when flight search fails."""

    def __init__(self, reason: str | None = None) -> None:
        message = (
            f"Flight search failed: {reason}" if reason else "Flight search failed"
        )
        super().__init__(message, "FLIGHT_SEARCH_ERROR")
        self.reason = reason


class FlightBookingError(FlightDomainError):
    """Raised when flight booking fails."""

    def __init__(self, reason: str | None = None, code: str | None = None) -> None:
        message = (
            f"Flight booking failed: {reason}" if reason else "Flight booking failed"
        )
        super().__init__(message, code or "FLIGHT_BOOKING_ERROR")
        self.reason = reason


class FlightBookingSupplierSyncError(FlightDomainError):
    """Supplier accepted the booking but Voya could not update the stored booking row (split-brain).

    Maps to HTTP 409 Conflict. Clients must not auto-retry payment; user should refresh or contact support.
    """

    def __init__(self, reason: str | None = None) -> None:
        message = reason or (
            "Could not confirm your booking in our system after the supplier accepted it."
        )
        super().__init__(message, "SUPPLIER_SYNC_CONFLICT")
        self.reason = reason


class FlightValidationError(FlightDomainError):
    """Raised when flight data validation fails."""

    def __init__(self, field: str | None = None, reason: str | None = None) -> None:
        if field and reason:
            message = f"Flight validation failed for {field}: {reason}"
        elif field:
            message = f"Invalid value for flight field: {field}"
        else:
            message = "Flight data validation failed"
        super().__init__(message, "FLIGHT_VALIDATION_ERROR")
        self.field = field
        self.reason = reason


class FlightApiError(FlightDomainError):
    """Raised when FlightLogic API returns an error."""

    def __init__(
        self, reason: str | None = None, status_code: int | None = None
    ) -> None:
        if status_code and reason:
            message = f"FlightLogic API error ({status_code}): {reason}"
        elif status_code:
            message = f"FlightLogic API error: HTTP {status_code}"
        else:
            message = (
                f"FlightLogic API error: {reason}"
                if reason
                else "FlightLogic API error"
            )
        super().__init__(message, "FLIGHT_API_ERROR")
        self.reason = reason
        self.status_code = status_code


class PaymentRequiredError(FlightDomainError):
    """Raised when payment is required but not provided."""

    def __init__(self, fare_type: str | None = None) -> None:
        if fare_type == "WebFare":
            message = "Payment required before booking LCC flights. Please complete payment first."
        elif fare_type in ["Public", "Private"]:
            message = "Payment required before issuing tickets. Please complete payment first."
        else:
            message = (
                "Payment required for this operation. Please complete payment first."
            )
        super().__init__(message, "PAYMENT_REQUIRED_ERROR")
        self.fare_type = fare_type
