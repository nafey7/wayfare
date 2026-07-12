"""Common schemas and data models."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field

from app.shared.schemas import StrictModel

# ==============================================================================
# CONSTANTS
# ==============================================================================

MINUTES_PER_HOUR = 60

T = TypeVar("T")

# ==============================================================================
# API RESPONSE MODELS
# ==============================================================================


class MessageResponse(StrictModel):
    """Simple message response."""

    message: str
    success: bool = True


class ErrorDetails(BaseModel):
    """Error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")


class ApiResponse[T](BaseModel):
    """Generic API response wrapper."""

    success: bool = Field(..., description="Operation success status")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[ErrorDetails] = Field(None, description="Error details if failed")


# ==============================================================================
# DATA MODELS
# ==============================================================================


class Address(StrictModel):
    """Address information."""

    street: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=3, max_length=10)


class MoneyAmount(BaseModel):
    """Monetary amount with currency and precision."""

    amount: Decimal = Field(..., description="Amount with precision")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="ISO 4217 currency code"
    )
    decimal_places: int = Field(
        2, ge=0, le=4, description="Number of decimal places (0-4)"
    )

    @property
    def formatted(self) -> str:
        """Get formatted amount string with proper decimal precision."""
        format_str = f"{{:,.{self.decimal_places}f}}"
        return f"{self.currency} {format_str.format(self.amount)}"


class Duration(BaseModel):
    """Duration information."""

    total_minutes: int = Field(..., description="Total duration in minutes")

    @property
    def formatted(self) -> str:
        """Get formatted duration like '2h 30m'."""
        if self.total_minutes < MINUTES_PER_HOUR:
            return f"{self.total_minutes}m"

        hours = self.total_minutes // MINUTES_PER_HOUR
        minutes = self.total_minutes % MINUTES_PER_HOUR

        if minutes == 0:
            return f"{hours}h"

        return f"{hours}h {minutes}m"


class PersonName(BaseModel):
    """Person name information."""

    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    title: Optional[str] = Field(None, max_length=20)

    @property
    def full_name(self) -> str:
        """Get full name with optional title."""
        parts = [self.title, self.first_name, self.last_name]
        return " ".join(part for part in parts if part)

    @property
    def display_name(self) -> str:
        """Get display name (First Last)."""
        return f"{self.first_name} {self.last_name}"


class DateTime(BaseModel):
    """DateTime wrapper with formatting utilities."""

    value: datetime = Field(..., description="DateTime object")

    @property
    def iso_string(self) -> str:
        """Get ISO 8601 formatted string."""
        return self.value.isoformat()


# ==============================================================================
# PAGINATION
# ==============================================================================


class PaginationRequest(BaseModel):
    """Standard pagination request parameters."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(20, ge=1, le=100, description="Items per page")


class PaginationResponse(BaseModel):
    """Pagination response metadata."""

    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, page: int, limit: int, total_items: int) -> "PaginationResponse":
        """Create pagination response from parameters."""
        total_pages = max(1, (total_items + limit - 1) // limit)

        return cls(
            page=page,
            limit=limit,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


__all__ = [
    "Address",
    "ApiResponse",
    "DateTime",
    "Duration",
    "EmailStr",
    "ErrorDetails",
    "MessageResponse",
    "MoneyAmount",
    "PaginationRequest",
    "PaginationResponse",
    "PersonName",
]
