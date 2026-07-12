"""Saved itineraries domain."""

from .repository import (
    SAVED_ITINERARIES_LIST_LIMIT,
    create_saved_itinerary,
    delete_saved_itinerary,
    ensure_saved_itinerary_owned_by_user,
    get_saved_itineraries_for_user,
    get_saved_itinerary_by_id,
    upsert_saved_itinerary_for_chat,
)
from .schemas import (
    LinkedBookingEventSummary,
    LinkedBookings,
    SavedItineraryCreate,
    SavedItineraryResponse,
)

__all__ = [
    "SAVED_ITINERARIES_LIST_LIMIT",
    "LinkedBookingEventSummary",
    "LinkedBookings",
    "SavedItineraryCreate",
    "SavedItineraryResponse",
    "create_saved_itinerary",
    "delete_saved_itinerary",
    "ensure_saved_itinerary_owned_by_user",
    "get_saved_itineraries_for_user",
    "get_saved_itinerary_by_id",
    "upsert_saved_itinerary_for_chat",
]
