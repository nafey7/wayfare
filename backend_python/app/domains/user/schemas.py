"""User schemas for API requests and responses."""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import ConfigDict, EmailStr, Field, field_validator

from app.domains.common import (
    Address,
    AuthProvider,
    validate_name,
    validate_phone,
)
from app.domains.passenger.schemas import PassengerMasked
from app.domains.user_preferences.schemas import UserPreferencesResponse
from app.shared.schemas import StrictModel

from .constants import ALLOWED_IMAGE_EXTENSIONS
from .enums import UserRole, UserStatus
from .validators import validate_timezone

if TYPE_CHECKING:
    from app.database.models.user import UserModel


# ============================================================
# HELPER MODELS (Components)
# ============================================================


class PhotoUrlsResponse(StrictModel):
    """Signed imgproxy URLs for the three profile-photo size presets."""

    sm: str  # 64x64 — header / chat
    md: str  # 128x128 — profile summary
    lg: str  # 256x256 — profile page main


class UserPhotoResponse(StrictModel):
    """Response body for PUT /api/user/me/photo."""

    photo_key: str
    photo_urls: PhotoUrlsResponse


class UserStatistics(StrictModel):
    """User statistics model."""

    bookings: int = 0
    searches: int = 0
    trips_created: int = 0
    messages_sent: int = 0
    api_calls_today: int = 0
    last_activity: datetime | None = None
    total_spent: float = 0.0
    account_age_days: int = 0
    login_streak: int = 0


# ============================================================
# REQUEST MODELS (API Input)
# ============================================================


class UserCreateRequest(StrictModel):
    """Request model for creating a user."""

    email: EmailStr
    first_name: str | None = Field(None, min_length=2, max_length=50)
    last_name: str | None = Field(None, min_length=2, max_length=50)
    mobile: str | None = None
    timezone: str | None = None
    address: Address | None = None

    @classmethod
    @field_validator("first_name", "last_name")
    def validate_names(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not validate_name(v):
            raise ValueError(
                "Name can only contain letters, spaces, hyphens, and apostrophes"
            )
        return v.strip()

    @classmethod
    @field_validator("mobile")
    def validate_mobile(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return validate_phone(v)
        except ValueError as e:
            raise ValueError("Invalid phone number format") from e

    @classmethod
    @field_validator("timezone")
    def validate_tz(cls, v: str | None) -> str | None:
        try:
            return validate_timezone(v)
        except Exception as e:
            raise ValueError(str(e)) from e


class UserUpdateRequest(StrictModel):
    """Request model for updating user profile."""

    first_name: str | None = Field(None, min_length=2, max_length=50)
    last_name: str | None = Field(None, min_length=2, max_length=50)
    mobile: str | None = None
    profile_image: str | None = None
    timezone: str | None = None
    address: Address | None = None
    travel_style_description: str | None = Field(None, max_length=500)

    @classmethod
    @field_validator("first_name", "last_name")
    def validate_names(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not validate_name(v):
            raise ValueError(
                "Name can only contain letters, spaces, hyphens, and apostrophes"
            )
        return v.strip()

    @classmethod
    @field_validator("mobile")
    def validate_mobile(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            return validate_phone(v)
        except ValueError as e:
            raise ValueError("Invalid phone number format") from e

    @classmethod
    @field_validator("timezone")
    def validate_tz(cls, v: str | None) -> str | None:
        try:
            return validate_timezone(v)
        except Exception as e:
            raise ValueError(str(e)) from e

    @classmethod
    @field_validator("profile_image")
    def validate_profile_image(cls, v: str | None) -> str | None:
        if v is None:
            return v

        # Check file extension
        if not any(v.lower().endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
            allowed = ", ".join(ALLOWED_IMAGE_EXTENSIONS)
            raise ValueError(f"Profile image must be one of: {allowed}")

        return v


class UserStatusUpdateRequest(StrictModel):
    """Request model for updating user status."""

    status: UserStatus


class UserPreferencesUpdateRequest(StrictModel):
    """Request model for updating user preferences."""

    notifications_enabled: bool | None = None
    newsletter_subscribed: bool | None = None
    language: str | None = None
    currency: str | None = None
    date_format: str | None = None


class UseDiscountRequest(StrictModel):
    """Request to use/apply the first-booking discount."""

    booking_amount: float  # Total booking amount in dollars (pre-discount)


class DiscountEligibilityResponse(StrictModel):
    """Response for discount eligibility check."""

    eligible: bool
    discount_amount: float = 50.0
    min_booking_amount: float = 600.0
    promotion_end_date: str = "2026-04-01"
    reason: str | None = None


# ============================================================
# RESPONSE MODELS (API Output)
# ============================================================


class UserBase(StrictModel):
    """Base user model with core fields."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    status: UserStatus
    role: UserRole = UserRole.USER
    email_verified: bool
    is_tester: bool = False
    discount_eligible: bool = False  # $50 first-booking discount eligibility (default False for existing users)
    created_at: datetime


class UserPublic(UserBase):
    """Public user model for API responses - excludes sensitive fields."""

    mobile: str | None = None
    profile_image: str | None = None
    photo_key: str | None = None
    photo_urls: PhotoUrlsResponse | None = None
    timezone: str | None = None
    address: Address | None = None
    auth_provider: AuthProvider
    last_login: datetime | None = None
    updated_at: datetime

    @classmethod
    def from_model(cls, user: "UserModel") -> "UserPublic":
        """Create User from database model."""
        from app.shared.imgproxy import build_avatar_urls

        photo_key = getattr(user, "photo_key", None)
        photo_urls_dict = build_avatar_urls(photo_key)
        photo_urls = PhotoUrlsResponse(**photo_urls_dict) if photo_urls_dict else None

        return cls(
            id=str(user.id) if user.id else "",
            email=user.email or "",
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image=user.profile_image,
            photo_key=photo_key,
            photo_urls=photo_urls,
            mobile=user.mobile,
            status=(
                UserStatus(user.status)
                if user.status in [s.value for s in UserStatus]
                else UserStatus.ACTIVE
            ),
            role=(
                UserRole(user.role)
                if user.role in [r.value for r in UserRole]
                else UserRole.USER
            ),
            email_verified=user.email_verified,
            is_tester=user.is_tester,
            discount_eligible=getattr(user, "discount_eligible", False),
            auth_provider=(
                AuthProvider(user.auth_provider)
                if user.auth_provider in [a.value for a in AuthProvider]
                else AuthProvider.LOCAL
            ),
            created_at=user.created_at or datetime.now(),
            updated_at=user.updated_at or datetime.now(),
            last_login=user.last_login,
            timezone=user.timezone,
            address=Address(**user.address) if user.address else None,
        )


class UserPrivate(UserPublic):
    """Private user schema with sensitive fields - for internal auth operations only."""

    password_hash: str | None = None
    password_reset_token: str | None = None
    password_reset_expires: datetime | None = None
    google_id: str | None = None

    @classmethod
    def from_model(cls, user: "UserModel") -> "UserPrivate":
        """Create UserPrivate from database model."""
        # Get all public fields from parent class
        public_data = UserPublic.from_model(user).model_dump()

        # Add private fields
        return cls(
            **public_data,
            password_hash=getattr(user, "password_hash", None),
            password_reset_token=getattr(user, "password_reset_token", None),
            password_reset_expires=getattr(user, "password_reset_expires", None),
            google_id=getattr(user, "google_id", None),
        )


class UserResponse(UserPublic):
    """Response model for user API endpoints."""

    # Subscription info
    plan_id: str | None = None
    subscription_id: str | None = None

    # Travel preferences
    travel_style_description: str | None = None

    # Statistics (optional)
    statistics: UserStatistics | None = None

    @classmethod
    def from_user(cls, user: UserPublic, **extra_fields) -> "UserResponse":
        """Create UserResponse from User with optional extra fields."""
        return cls(**user.model_dump(), **extra_fields)


# --- Profile aggregate (GET /api/user/me/profile) ---


class ProfileUserResponse(StrictModel):
    """Simplified user for profile page aggregate (header + basic info)."""

    id: str
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    profile_image: str | None = None
    photo_key: str | None = None
    photo_urls: PhotoUrlsResponse | None = None
    mobile: str | None = None

    @classmethod
    def from_user_public(cls, user: UserPublic) -> "ProfileUserResponse":
        """Create from UserPublic (subset of fields)."""
        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_image=user.profile_image,
            photo_key=user.photo_key,
            photo_urls=user.photo_urls,
            mobile=user.mobile,
        )


class ProfileAggregateResponse(StrictModel):
    """Aggregate response for GET /api/user/me/profile: user + preferences + passengers."""

    user: ProfileUserResponse
    preferences: UserPreferencesResponse
    passengers: list[PassengerMasked]
