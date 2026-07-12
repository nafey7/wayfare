"""Transit domain exceptions.

Custom exception classes for transit-specific errors, following the same patterns
as the flight and hotel domains for consistency.
"""


class TransitDomainError(Exception):
    """Base exception for all transit domain errors.

    All transit-specific exceptions inherit from this base class.
    """

    def __init__(
        self, message: str = "Transit error occurred", code: str | None = None
    ) -> None:
        """Initialize transit domain error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code
        """
        self.message = message
        self.code = code or "TRANSIT_ERROR"
        super().__init__(self.message)


class TransitRouteError(TransitDomainError):
    """Transit route operation failed.

    Raised when a transit route search cannot be completed successfully.
    """

    def __init__(self, reason: str | None = None) -> None:
        """Initialize transit route error.

        Args:
            reason: Specific reason for the route failure
        """
        message = (
            f"Transit route failed: {reason}" if reason else "Transit route failed"
        )
        super().__init__(message, "TRANSIT_ROUTE_ERROR")


class TransitValidationError(TransitDomainError):
    """Transit data validation failed.

    Raised when transit route parameters fail validation.
    """

    def __init__(self, field: str | None = None, reason: str | None = None) -> None:
        """Initialize transit validation error.

        Args:
            field: Name of the field that failed validation
            reason: Reason for validation failure
        """
        if field and reason:
            message = f"Validation failed for {field}: {reason}"
        else:
            message = "Transit validation failed"
        super().__init__(message, "TRANSIT_VALIDATION_ERROR")
