"""User model for MongoDB 'users' collection."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.database.types import PyObjectId


class UserModel(BaseModel):
    """User model matching MongoDB 'users' collection schema."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # MongoDB _id field
    id: PyObjectId | None = Field(default=None, alias="_id")

    # Core user fields
    email: EmailStr | None = None
    mobile: str | None = None
    password_hash: str | None = None  # Hashed password
    first_name: str | None = None
    last_name: str | None = None
    profile_image: str | None = None
    # S3 key for uploaded profile photo (private bucket; served via imgproxy).
    photo_key: str | None = None

    # Address fields
    address: dict[str, Any] | None = Field(
        default=None,
        description="User's address: {street, city, state, postal_code, country}",
    )

    # Authentication fields
    auth_provider: str = "local"
    google_id: str | None = None
    facebook_id: str | None = None
    email_verified: bool = False
    email_verification_token: str | None = None
    password_reset_token: str | None = None
    password_reset_expires: datetime | None = None

    # Status and verification
    status: int = (
        1  # UserStatus enum value (1=ACTIVE, 2=INACTIVE, 3=DELETED, 4=SUSPENDED)
    )
    role: str = "user"  # UserRole enum value (user, admin, super_admin)
    is_tester: bool = False  # Whether user should use test environments
    failed_login_attempts: int = 0
    account_locked_until: datetime | None = None

    # Subscription related
    stripe_customer_id: str | None = None
    plan_id: PyObjectId | None = None
    subscription_id: PyObjectId | None = None

    # Promotional discount eligibility
    # True = user can use the $50 first-booking discount (for bookings >= $600 before April 1, 2026)
    # Default False for existing users; set to True during signup for new users
    # Set to False after first successful booking with discount applied
    discount_eligible: bool = False

    # Metadata
    last_login: datetime | None = None
    last_login_ip: str | None = None
    timezone: str | None = None  # Future: for scheduling and time display
    created_at: datetime | None = None
    updated_at: datetime | None = None
