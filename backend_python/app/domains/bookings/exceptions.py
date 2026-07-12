"""Bookings domain exceptions."""


class BookingForbiddenError(Exception):
    """Raised when the authenticated user does not own the requested booking."""


class GdsPendingBookingSyncError(Exception):
    """Raised when FlightLogic booking succeeded but the PENDING MongoDB row could not be updated.

    Callers should fail the booking response so the client does not assume Voya state matches the supplier.
    """


class MalformedBookingEventDocumentError(Exception):
    """Raised when a ``booking_events`` document lacks fields required for API mapping."""


class GdsClientReferenceConflictError(Exception):
    """Raised when ``client_reference`` is ``VOYA-*`` but the stored row is not PENDING + TEMP-REF.

    Do not call FlightLogic — avoids duplicate or inconsistent supplier bookings when the UI is stale
    or the reference was already completed/cancelled.
    """

    DEFAULT_MESSAGE = (
        "This booking reference is not in a valid state to complete payment. "
        "Please refresh the booking page or contact support if the problem persists."
    )

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.DEFAULT_MESSAGE)
