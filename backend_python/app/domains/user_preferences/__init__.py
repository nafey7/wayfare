"""User preferences domain.

Stores travel preferences per user: travel style, flights, hotels.
"""

from .repository import get_preferences, upsert_preferences
from .schemas import (
    FlightsPreferences,
    FlightsPreferencesUpdate,
    HotelsPreferences,
    PreferencesUpdateRequest,
    TravelStylePreferences,
    UserPreferencesResponse,
)

__all__ = [
    "FlightsPreferences",
    "FlightsPreferencesUpdate",
    "HotelsPreferences",
    "PreferencesUpdateRequest",
    "TravelStylePreferences",
    "UserPreferencesResponse",
    "get_preferences",
    "upsert_preferences",
]
