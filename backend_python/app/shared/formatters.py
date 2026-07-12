"""Formatting functions for data transformation and normalization.

This module provides formatting utilities that are used across the application.
For validation functions, see app.domains.common.standards.
"""

import re
from datetime import date
from decimal import Decimal

# ==============================================================================
# PHONE NUMBER FORMATTING
# ==============================================================================


def clean_phone_number(phone: str) -> str:
    """Clean and normalize phone number - basic version.

    Note: For full international parsing, use standards.clean_phone_number

    Args:
        phone: Raw phone number string

    Returns:
        Cleaned phone number without spaces/hyphens
    """
    return phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")


def format_phone_for_validation(phone: str) -> str:
    """Format phone number for regex validation.

    Args:
        phone: Phone number to format

    Returns:
        Phone number ready for pattern matching
    """
    return clean_phone_number(phone)


def extract_phone_digits(phone: str) -> str:
    """Extract only digit characters from phone number.

    Args:
        phone: Phone number with possible formatting

    Returns:
        Digits only, excluding country code prefix
    """
    if phone.startswith("+"):
        phone = phone[1:]
    return "".join(c for c in phone if c.isdigit())


# ==============================================================================
# TEXT FORMATTING
# ==============================================================================


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated text with suffix if needed
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def capitalize_words(text: str, exceptions: list[str] | None = None) -> str:
    """Capitalize each word with exceptions for articles/prepositions.

    Args:
        text: Text to capitalize
        exceptions: Words to keep lowercase (e.g., ['van', 'de', 'la'])

    Returns:
        Title cased text with exceptions
    """
    if not text:
        return text

    exceptions = exceptions or []
    words = text.split()
    result = []

    for i, word in enumerate(words):
        if i == 0 or word.lower() not in exceptions:
            result.append(word.capitalize())
        else:
            result.append(word.lower())

    return " ".join(result)


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Lowercase slug with hyphens
    """

    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


# ==============================================================================
# DATE FORMATTING
# ==============================================================================


def format_date_range(start_date: date, end_date: date) -> str:
    """Format date range for display.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Formatted date range string
    """
    if start_date == end_date:
        return start_date.strftime("%B %d, %Y")

    if start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return f"{start_date.strftime('%B %d')} - {end_date.strftime('%d, %Y')}"
        return f"{start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}"

    return f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"


def format_duration_display(minutes: int) -> str:
    """Format duration in minutes to human readable.

    Args:
        minutes: Duration in minutes

    Returns:
        Human readable duration (e.g., '2h 30m', '45m')
    """
    MINUTES_PER_HOUR = 60
    if minutes < MINUTES_PER_HOUR:
        return f"{minutes}m"

    hours = minutes // MINUTES_PER_HOUR
    remaining_minutes = minutes % MINUTES_PER_HOUR

    if remaining_minutes == 0:
        return f"{hours}h"

    return f"{hours}h {remaining_minutes}m"


# ==============================================================================
# NUMERIC FORMATTING
# ==============================================================================


def format_price_display(amount: Decimal | float | None, currency: str = "EUR") -> str:
    """Format price for display with currency symbol.

    Args:
        amount: Price amount, None returns 'N/A'
        currency: Currency code

    Returns:
        Formatted price string
    """
    if amount is None:
        return "N/A"

    # Simple currency symbols mapping
    symbols = {
        "EUR": "€",
        "USD": "$",
        "GBP": "£",
        "JPY": "¥",
    }

    symbol = symbols.get(currency.upper(), currency)
    return f"{symbol}{amount:,.2f}"


def format_percentage_display(value: float | None, decimals: int = 1) -> str:
    """Format decimal as percentage for display.

    Args:
        value: Decimal value (0.15 = 15%)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"

    percentage = value * 100
    return f"{percentage:.{decimals}f}%"


# ==============================================================================
# EXPORTS
# ==============================================================================

__all__ = [
    "capitalize_words",
    "clean_phone_number",
    "extract_phone_digits",
    "format_date_range",
    "format_duration_display",
    "format_percentage_display",
    "format_phone_for_validation",
    "format_price_display",
    "slugify",
    "truncate_text",
]
