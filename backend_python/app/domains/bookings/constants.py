"""Constants for booking log domain."""

from enum import StrEnum

# MongoDB collection name
BOOKING_EVENT_COLLECTION = "booking_events"

# Placeholder for LCC: booking event created after payment, before FlightLogic booking API
TEMP_EXTERNAL_REF = "TEMP-REF"


class BookingEventType(StrEnum):
    """Types of booking events."""

    # Transportation
    FLIGHT = "FLIGHT"
    TRAIN = "TRAIN"
    BUS = "BUS"
    FERRY = "FERRY"
    CAR_RENTAL = "CAR_RENTAL"
    TAXI = "TAXI"

    # Accommodation
    HOTEL = "HOTEL"
    HOSTEL = "HOSTEL"
    APARTMENT = "APARTMENT"
    AIRBNB = "AIRBNB"

    # Activities
    TOUR = "TOUR"
    ACTIVITY = "ACTIVITY"
    RESTAURANT = "RESTAURANT"
    EVENT = "EVENT"

    # Meta events
    NOTE = "NOTE"
    CHECKIN = "CHECKIN"
    BORDER_CROSSING = "BORDER_CROSSING"
    VISA = "VISA"
    INSURANCE = "INSURANCE"

    # Planning
    PLANNED_ROUTE = "PLANNED_ROUTE"
    WISHLIST = "WISHLIST"


class EventStatus(StrEnum):
    """Status of a booking event."""

    PLANNED = "PLANNED"  # Future, not confirmed
    CONFIRMED = "CONFIRMED"  # Booked and confirmed
    IN_PROGRESS = "IN_PROGRESS"  # Currently happening
    COMPLETED = "COMPLETED"  # Past event
    CANCELLED = "CANCELLED"  # Was planned but cancelled
    MODIFIED = "MODIFIED"  # Changed (creates new event)


class EventVisibility(StrEnum):
    """Who can see this event."""

    PRIVATE = "PRIVATE"  # Only user
    COMPANIONS = "COMPANIONS"  # User and travel companions
    FRIENDS = "FRIENDS"  # User's friends
    PUBLIC = "PUBLIC"  # Anyone
