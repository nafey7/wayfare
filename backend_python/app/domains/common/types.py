"""Core utilities and validation functions."""

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import phonenumbers
import pycountry
from phonenumbers import NumberParseException, PhoneNumberFormat

from .enums import AuthProvider, GenderCode, TravelTitle

# ==============================================================================
# CONSTANTS
# ==============================================================================

MINUTES_PER_HOUR = 60
ISO_COUNTRY_CODE_2_CHARS = 2
ISO_COUNTRY_CODE_3_CHARS = 3


# ==============================================================================
# DATETIME UTILITIES
# ==============================================================================


def now_utc() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


def utc_date() -> date:
    """Get current UTC date."""
    return datetime.now(UTC).date()


# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================


def normalize_email(email: str) -> str:
    """Normalize email address to lowercase."""
    return email.lower().strip()


def validate_email(email: str) -> str:
    """Normalize email address to lowercase (deprecated, use normalize_email)."""
    return normalize_email(email)


def validate_phone(phone: str, country_code: str | None = None) -> str:
    """Validate and clean international phone number.

    Args:
        phone: Phone number to validate (e.g., "+31 6 12345678", "06-12345678")
        country_code: Optional country hint for parsing (e.g., "NL", "US")

    Returns:
        Cleaned phone number in E.164 format (e.g., "+31612345678")

    Raises:
        ValueError: If phone number is invalid

    Example:
        >>> validate_phone("+31 6 12345678")
        "+31612345678"
        >>> validate_phone("06-12345678", "NL")
        "+31612345678"
    """
    try:
        parsed = phonenumbers.parse(phone, country_code)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number: {phone}")
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    except NumberParseException as e:
        raise ValueError(f"Invalid phone format: {e}") from e


def validate_country_code(code: str) -> bool:
    """Validate ISO 3166-1 country code."""
    try:
        if len(code) == ISO_COUNTRY_CODE_2_CHARS:
            return pycountry.countries.get(alpha_2=code.upper()) is not None
        if len(code) == ISO_COUNTRY_CODE_3_CHARS:
            return pycountry.countries.get(alpha_3=code.upper()) is not None
        return False
    except (AttributeError, LookupError):
        return False


def validate_name(name: str) -> bool:
    """Check if name contains only valid characters."""
    if not name:
        return True
    return bool(re.match(r"^[a-zA-Z\s\-'.]+$", name.strip()))


def validate_future_date(date_value: date, min_days_ahead: int = 0) -> None:
    """Validate that date is in the future.

    Args:
        date_value: Date to validate
        min_days_ahead: Minimum days from today (default 0 = today or later)

    Raises:
        ValueError: If date is not far enough in future

    Example:
        >>> from datetime import date, timedelta
        >>> tomorrow = date.today() + timedelta(days=1)
        >>> validate_future_date(tomorrow)  # No exception
        >>> validate_future_date(tomorrow, min_days_ahead=7)  # ValueError
    """
    today = utc_date()

    if min_days_ahead == 0:
        if date_value < today:
            raise ValueError("Date must be today or in the future")
    else:
        min_date = today + timedelta(days=min_days_ahead)
        if date_value < min_date:
            raise ValueError(
                f"Date must be at least {min_days_ahead} days in the future"
            )


# ==============================================================================
# FORMATTING FUNCTIONS
# ==============================================================================


def format_phone_display(phone: str) -> str:
    """Format phone number for display in international format.

    Example:
        >>> format_phone_display("+31612345678")
        "+31 6 12 34 56 78"
    """
    try:
        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    except NumberParseException:
        return phone


def format_duration_minutes(total_minutes: int) -> str:
    """Format duration in minutes to human-readable string like '2h 30m'.

    Example:
        >>> format_duration_minutes(150)
        "2h 30m"
        >>> format_duration_minutes(45)
        "45m"
    """
    if total_minutes < MINUTES_PER_HOUR:
        return f"{total_minutes}m"

    hours = total_minutes // MINUTES_PER_HOUR
    minutes = total_minutes % MINUTES_PER_HOUR

    if minutes == 0:
        return f"{hours}h"

    return f"{hours}h {minutes}m"


def format_money(
    amount: Decimal | float | int | str | None, currency: str = "USD"
) -> str:
    """Format monetary amount with currency code.

    Handles string input (e.g. from FlightLogic API) by converting to float.
    """
    if amount is None:
        return f"{currency} 0.00"
    if isinstance(amount, str):
        try:
            # Remove common formatting (commas, spaces) before parsing
            cleaned = amount.replace(",", "").replace(" ", "").strip()
            amount = float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return f"{currency} 0.00"
    elif isinstance(amount, Decimal):
        amount = float(amount)
    return f"{currency} {amount:,.2f}"


__all__ = [
    "AuthProvider",
    "GenderCode",
    "TravelTitle",
    "format_duration_minutes",
    "format_money",
    "format_phone_display",
    "now_utc",
    "utc_date",
    "validate_country_code",
    "validate_email",
    "validate_future_date",
    "validate_name",
    "validate_phone",
]
