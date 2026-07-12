"""Common domain functionality.

Essential utilities, validation, and schemas used across domains.
"""

# Standard library
from datetime import UTC, datetime, timedelta

# Local imports
from .enums import AuthProvider, GenderCode, TravelTitle
from .schemas import (
    Address,
    ApiResponse,
    DateTime,
    Duration,
    EmailStr,
    ErrorDetails,
    MessageResponse,
    MoneyAmount,
    PaginationRequest,
    PaginationResponse,
    PersonName,
)
from .types import (
    format_duration_minutes,
    format_money,
    format_phone_display,
    normalize_email,
    now_utc,
    utc_date,
    validate_country_code,
    validate_email,
    validate_future_date,
    validate_name,
    validate_phone,
)

__all__ = [
    # Standard library re-exports
    "UTC",
    # Data models
    "Address",
    "ApiResponse",
    # Core enums
    "AuthProvider",
    "DateTime",
    "Duration",
    "EmailStr",
    "ErrorDetails",
    "GenderCode",
    "MessageResponse",
    "MoneyAmount",
    "PaginationRequest",
    "PaginationResponse",
    "PersonName",
    "TravelTitle",
    "datetime",
    # Utility functions
    "format_duration_minutes",
    "format_money",
    "format_phone_display",
    "normalize_email",
    "now_utc",
    "timedelta",
    "utc_date",
    "validate_country_code",
    "validate_email",
    "validate_future_date",
    "validate_name",
    "validate_phone",
]
