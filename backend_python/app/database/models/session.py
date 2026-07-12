"""Session model for MongoDB 'sessions' collection."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.database.types import PyObjectId


class SessionModel(BaseModel):
    """Session model matching MongoDB 'sessions' collection."""

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    # MongoDB _id field
    id: PyObjectId | None = Field(default=None, alias="_id")

    # Session fields
    user_id: PyObjectId | None = None
    fingerprint: str | None = None
    parameters: dict[str, Any] | None = None
    status: int = 1  # 1=ACTIVE, 2=EXPIRED, 3=REVOKED

    # Token fields
    access_token: str | None = None
    refresh_token: str | None = None
    access_token_expires: datetime | None = None
    refresh_token_expires: datetime | None = None

    # Security fields
    ip_address: str | None = None
    user_agent: str | None = None
    device_id: str | None = None
    is_remembered: bool = False

    # Timestamps
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_activity: datetime | None = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: Any) -> int:
        """Validate status is a valid integer."""
        if isinstance(v, int) and 1 <= v <= 3:
            return v
        return 1  # Default to ACTIVE

    def is_expired(self) -> bool:
        """Check if session is expired."""
        if self.access_token_expires:
            return datetime.now(UTC) > self.access_token_expires
        return True

    def is_refresh_token_valid(self) -> bool:
        """Check if refresh token is still valid."""
        if self.refresh_token_expires:
            return datetime.now(UTC) < self.refresh_token_expires
        return False
