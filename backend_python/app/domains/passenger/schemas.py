"""Passenger storage schemas.

PII classification per issue #418:
- Sensitive (encrypted): passport_number, passport_expiry, frequent_flyer_number
- Standard: first_name, last_name, title, date_of_birth, nationality, email, phone
"""

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# Fields that must be encrypted at rest (sensitive PII per GDPR)
ENCRYPTED_FIELDS = frozenset(
    {"passport_number", "passport_expiry", "frequent_flyer_number"}
)


def mask_sensitive(value: str | None) -> str:
    """Mask sensitive value for API response. E.g. 'AB1234567' -> '****4567'."""  # pragma: allowlist secret
    if not value or len(value) < 4:
        return "****"
    return "****" + value[-4:]


def mask_date(value: str | None) -> str:
    """Mask date for API response. E.g. '2028-05-15' -> '2028-**-**'."""
    if not value:
        return "****-**-**"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value[:5] + "**-**"
    return "****-**-**"


class PassengerCreate(BaseModel):
    """Schema for creating a stored passenger."""

    is_primary: bool = Field(False, description="Account owner (self) passenger")
    title: str = Field(..., min_length=1, max_length=20)
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    date_of_birth: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="YYYY-MM-DD format",
    )
    nationality: str = Field(..., min_length=2, max_length=2)
    email: EmailStr | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    passport_number: str | None = Field(None, max_length=50)
    passport_expiry: str | None = Field(None, max_length=10)
    passport_country: str | None = Field(None, min_length=2, max_length=2)
    frequent_flyer_number: str | None = Field(None, max_length=50)
    type: str | None = Field(
        None,
        description="Passenger type: adult, child, or infant",
    )

    @field_validator("nationality", "passport_country")
    @classmethod
    def validate_country_code(cls, v: str | None) -> str | None:
        """Ensure 2-letter ISO country code."""
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError("Use 2-letter ISO country code")
        return v.upper()

    @field_validator("passport_expiry")
    @classmethod
    def validate_passport_expiry(cls, v: str | None) -> str | None:
        """Optional YYYY-MM-DD format."""
        if not v:
            return v
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return v
        raise ValueError("Passport expiry must be YYYY-MM-DD")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        """Validate passenger type."""
        if v is None:
            return v
        allowed = ("adult", "child", "infant")
        if v.lower() not in allowed:
            raise ValueError(f"Type must be one of {allowed}")
        return v.lower()

    @model_validator(mode="after")
    def validate_title_for_type(self) -> "PassengerCreate":
        """Validate title matches type: adult → Mr/Mrs/Miss/Ms; child/infant → Master/Miss."""
        if not self.type:
            return self
        t = self.title.strip().lower()
        if self.type == "adult":
            if t not in ("mr", "mrs", "miss", "ms"):
                raise ValueError("Adult must have title Mr, Mrs, Miss, or Ms")
        elif t not in ("master", "miss"):
            raise ValueError("Child/infant must have title Master or Miss")
        return self


class PassengerUpdate(BaseModel):
    """Schema for updating a stored passenger. All fields optional."""

    is_primary: bool | None = Field(None, description="Account owner (self) passenger")
    title: str | None = Field(None, min_length=1, max_length=20)
    first_name: str | None = Field(None, min_length=2, max_length=50)
    last_name: str | None = Field(None, min_length=2, max_length=50)
    date_of_birth: str | None = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    nationality: str | None = Field(None, min_length=2, max_length=2)
    email: EmailStr | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    passport_number: str | None = Field(None, max_length=50)
    passport_expiry: str | None = Field(None, max_length=10)
    passport_country: str | None = Field(None, min_length=2, max_length=2)
    frequent_flyer_number: str | None = Field(None, max_length=50)
    type: str | None = Field(None)

    @field_validator("nationality", "passport_country")
    @classmethod
    def validate_country_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) != 2:
            raise ValueError("Use 2-letter ISO country code")
        return v.upper()

    @field_validator("passport_expiry")
    @classmethod
    def validate_passport_expiry(cls, v: str | None) -> str | None:
        if not v:
            return v
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return v
        raise ValueError("Passport expiry must be YYYY-MM-DD")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = ("adult", "child", "infant")
        if v.lower() not in allowed:
            raise ValueError(f"Type must be one of {allowed}")
        return v.lower()

    @model_validator(mode="after")
    def validate_title_for_type(self) -> "PassengerUpdate":
        """Validate title matches type when both provided."""
        title = self.title
        type_val = self.type
        if title is None or type_val is None:
            return self
        t = title.strip().lower()
        if type_val == "adult":
            if t not in ("mr", "mrs", "miss", "ms"):
                raise ValueError("Adult must have title Mr, Mrs, Miss, or Ms")
        elif t not in ("master", "miss"):
            raise ValueError("Child/infant must have title Master or Miss")
        return self


class PassengerMasked(BaseModel):
    """Passenger response with sensitive fields masked (for list/detail)."""

    id: str
    user_id: str
    is_primary: bool = False
    title: str
    hotel_title: str
    type_hotel: str
    first_name: str
    last_name: str
    date_of_birth: str
    nationality: str
    email: str | None = None
    phone: str | None = None
    passport_number: str | None = None  # Masked: ****4589
    passport_expiry: str | None = None  # Masked: 2028-**-**
    passport_country: str | None = None
    frequent_flyer_number: str | None = None  # Masked: ****7890
    type: str | None = None
    created_at: datetime
    updated_at: datetime


class PassengerResponse(BaseModel):
    """Passenger with full values (for booking confirmation only)."""

    id: str
    user_id: str
    is_primary: bool = False
    title: str
    hotel_title: str
    type_hotel: str
    first_name: str
    last_name: str
    date_of_birth: str
    nationality: str
    email: str | None = None
    phone: str | None = None
    passport_number: str | None = None
    passport_expiry: str | None = None
    passport_country: str | None = None
    frequent_flyer_number: str | None = None
    type: str | None = None
    created_at: datetime
    updated_at: datetime
