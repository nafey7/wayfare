"""Session state model for booking conversations.

This module defines the SessionState Pydantic model that serves as the single
source of truth for all booking session data. It consolidates state that was
previously scattered across:

1. Handler's session_store dict (in-memory)
2. FieldCollector's collected_data dict (in-memory)
3. MongoDB booking_sessions collection

By using this model exclusively with MongoDB, we eliminate data resurrection bugs
caused by merging stale in-memory state with persistent storage.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SessionType(StrEnum):
    """Type of booking session."""

    FLIGHT = "flight"
    HOTEL = "hotel"


class SessionState(BaseModel):
    """Single source of truth for booking session state.

    This model captures all state needed for a booking conversation:
    - Collected booking fields (origin, destination, dates, passengers, etc.)
    - Field collector state (what field we're waiting for, pending confirmations)
    - Booking flow state (current stage in the booking process)
    - Conversation context

    All state is persisted to MongoDB via SessionStateManager.
    """

    session_id: str
    user_id: str
    session_type: SessionType

    # Collected booking fields (origin, destination, dates, passengers, etc.)
    collected: dict[str, Any] = Field(default_factory=dict)

    # Field collector state (moved from FlightFieldCollector/HotelFieldCollector)
    waiting_for_field: str | None = None
    waiting_for_airport_selection: str | None = (
        None  # Flight: which field needs airport
    )
    pending_date_range: dict[str, Any] | None = None  # Flight: date range confirmation
    pending_disambiguation: list[dict[str, Any]] | None = None  # Hotel: city options
    last_question: str | None = None  # Last question asked to user

    # Booking flow state
    booking_stage: str | None = None  # e.g., "search", "selection", "passenger_details"
    selected_option_index: int | None = None  # Which flight/hotel option was selected

    # Conversation context
    context: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def update_collected(self, **fields: Any) -> None:
        """Update collected fields, filtering out None values."""
        for key, value in fields.items():
            if value is not None:
                self.collected[key] = value
        self.updated_at = datetime.now(UTC)

    def clear_collector_state(self) -> None:
        """Clear field collector state (used when resetting for new search)."""
        self.waiting_for_field = None
        self.waiting_for_airport_selection = None
        self.pending_date_range = None
        self.pending_disambiguation = None
        self.last_question = None
        self.updated_at = datetime.now(UTC)

    def to_mongo_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return self.model_dump(mode="json")

    @classmethod
    def from_mongo_dict(cls, data: dict[str, Any]) -> "SessionState":
        """Create from MongoDB document."""
        return cls.model_validate(data)
