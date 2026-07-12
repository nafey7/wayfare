"""User validation logic."""

from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

from app.domains.common import utc_date, validate_name, validate_phone

from .constants import MAX_AGE, MIN_AGE
from .exceptions import (
    EmailAlreadyExistsError,
    InvalidAddressError,
    InvalidPhoneNumberError,
    ValidationError,
)


def validate_name_characters(name: str) -> None:
    """Validate that name contains only allowed characters."""
    if not validate_name(name):
        raise ValidationError("Name contains invalid characters")


def validate_phone_number(phone: str) -> None:
    """Validate international phone number format."""
    try:
        validate_phone(phone)
    except ValueError as e:
        raise InvalidPhoneNumberError(str(e)) from e


def validate_date_of_birth(dob: datetime) -> None:
    """Validate date of birth and age requirements."""
    today = utc_date()
    birth_date = dob.date() if isinstance(dob, datetime) else dob
    age = today.year - birth_date.year

    # Adjust if birthday hasn't occurred this year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1

    if age < MIN_AGE:
        raise ValidationError(f"Must be at least {MIN_AGE} years old")

    if age > MAX_AGE:
        raise ValidationError("Invalid date of birth")


def validate_profile_image_url(image_url: str) -> None:
    """Validate profile image URL for HTTPS requirement."""
    if not image_url:
        return

    if not image_url.startswith("https://"):
        raise ValidationError("Profile image must use HTTPS for security")


def validate_timezone(timezone: str | None) -> str | None:
    """Validate timezone string against zoneinfo database."""
    if timezone is None:
        return None

    try:
        # Try to create a ZoneInfo object to validate
        ZoneInfo(timezone)
        return timezone
    except Exception:
        # For better error message, check if it's close to a valid timezone
        available = available_timezones()
        suggestions = [tz for tz in available if timezone.lower() in tz.lower()][:3]
        if suggestions:
            raise ValidationError(
                f"Invalid timezone '{timezone}'. Did you mean: {', '.join(suggestions)}?"
            ) from None
        raise ValidationError(f"Invalid timezone: {timezone}") from None


def validate_postal_code(postal_code: str, _country_code: str) -> None:
    """Validate postal code based on country."""
    if not postal_code:
        return

    # Simple validation - can be enhanced later
    if len(postal_code) < 3 or len(postal_code) > 10:
        raise InvalidAddressError("Postal code must be between 3 and 10 characters")


async def validate_email_uniqueness(email: str) -> None:
    """Validate that email is unique in database."""
    from . import repository

    if await repository.email_exists(email):
        raise EmailAlreadyExistsError(email)
