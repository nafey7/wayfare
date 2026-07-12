"""Validation utilities for flight bookings.

This module provides shared validation functions for flight-related operations,
including ticket time limit validation used across payment and flight domains.
"""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def validate_ticket_time_limit(
    ticket_time_limit: datetime | None, buffer_minutes: int = 5
) -> tuple[bool, int | None]:
    """Validate ticket time limit against current time.

    Checks if the ticket time limit has expired, accounting for a buffer
    to handle processing time and clock skew.

    Args:
        ticket_time_limit: Ticket time limit datetime (should be UTC, but will be normalized)
        buffer_minutes: Buffer in minutes before expiry (default: 5 minutes)

    Returns:
        Tuple of (is_valid, seconds_remaining):
        - is_valid: True if booking is still valid, False if expired
        - seconds_remaining: Seconds remaining until expiry (None if no limit or expired)

    Note:
        - If ticket_time_limit is None, returns (True, None) - booking is valid
        - Normalizes timezone to UTC if needed
        - Uses buffer to account for processing time and clock skew
    """
    if ticket_time_limit is None:
        return (True, None)

    current_time_utc = datetime.now(UTC)
    ticket_time_limit_utc = ticket_time_limit

    # Ensure ticket_time_limit is timezone-aware (should be UTC)
    if ticket_time_limit_utc.tzinfo is None:
        ticket_time_limit_utc = ticket_time_limit_utc.replace(tzinfo=UTC)
    else:
        # Convert to UTC if it's in a different timezone
        ticket_time_limit_utc = ticket_time_limit_utc.astimezone(UTC)

    # Compare with buffer to account for processing time and clock skew
    buffer_seconds = buffer_minutes * 60
    expired_time = ticket_time_limit_utc.timestamp() - buffer_seconds

    if current_time_utc.timestamp() > expired_time:
        return (False, 0)

    time_remaining = int(expired_time - current_time_utc.timestamp())
    return (True, time_remaining)
