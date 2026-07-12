"""Hotel domain exceptions.

Custom exception classes for hotel-specific errors, following the same patterns
as the flight domain for consistency.
"""


class HotelDomainError(Exception):
    """Base exception for all hotel domain errors.

    All hotel-specific exceptions inherit from this base class.
    """

    def __init__(
        self, message: str = "Hotel error occurred", code: str | None = None
    ) -> None:
        """Initialize hotel domain error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        self.message = message
        self.code = code or "HOTEL_ERROR"
        super().__init__(self.message)


class HotelSearchError(HotelDomainError):
    """Hotel search operation failed.

    Raised when a hotel search cannot be completed successfully.
    """

    def __init__(self, reason: str | None = None) -> None:
        """Initialize hotel search error.

        Args:
            reason: Specific reason for the search failure
        """
        message = f"Hotel search failed: {reason}" if reason else "Hotel search failed"
        super().__init__(message, "HOTEL_SEARCH_ERROR")


class HotelValidationError(HotelDomainError):
    """Hotel data validation failed.

    Raised when hotel search or booking parameters fail validation.
    """

    def __init__(self, field: str | None = None, reason: str | None = None) -> None:
        """Initialize hotel validation error.

        Args:
            field: Name of the field that failed validation
            reason: Reason for validation failure
        """
        if field and reason:
            message = f"Validation failed for {field}: {reason}"
        else:
            message = "Hotel validation failed"
        super().__init__(message, "HOTEL_VALIDATION_ERROR")


class HotelSessionError(HotelDomainError):
    """Hotel session-related error.

    Raised when there are issues with hotel search sessions (e.g., expired, invalid).
    """

    def __init__(self, reason: str | None = None) -> None:
        """Initialize hotel session error.

        Args:
            reason: Specific reason for the session error
        """
        message = f"Hotel session error: {reason}" if reason else "Hotel session error"
        super().__init__(message, "HOTEL_SESSION_ERROR")


class HotelBookingError(HotelDomainError):
    """Hotel booking operation failed.

    Raised when a hotel booking cannot be created or processed.
    """

    def __init__(self, reason: str | None = None) -> None:
        """Initialize hotel booking error.

        Args:
            reason: Specific reason for the booking failure
        """
        message = (
            f"Hotel booking failed: {reason}" if reason else "Hotel booking failed"
        )
        super().__init__(message, "HOTEL_BOOKING_ERROR")


class HotelNotFoundError(HotelDomainError):
    """Requested hotel not found.

    Raised when a hotel lookup fails to find the requested hotel.
    """

    def __init__(self, hotel_id: str | None = None) -> None:
        """Initialize hotel not found error.

        Args:
            hotel_id: ID of the hotel that wasn't found
        """
        message = f"Hotel not found: {hotel_id}" if hotel_id else "Hotel not found"
        super().__init__(message, "HOTEL_NOT_FOUND")


class HotelRateError(HotelDomainError):
    """Hotel rate/pricing error.

    Raised when there are issues with hotel rates (e.g., price changed, rate unavailable).
    """

    def __init__(self, reason: str | None = None) -> None:
        """Initialize hotel rate error.

        Args:
            reason: Specific reason for the rate error
        """
        message = f"Hotel rate error: {reason}" if reason else "Hotel rate error"
        super().__init__(message, "HOTEL_RATE_ERROR")
