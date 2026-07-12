"""Passenger details storage domain.

Stores passenger/guest details per user with field-level encryption for sensitive PII.
See GitHub issue #418.
"""

from .repository import (
    create_passenger,
    delete_passenger,
    get_passenger_by_id,
    get_passengers_for_user,
    update_passenger,
)
from .schemas import (
    PassengerCreate,
    PassengerMasked,
    PassengerResponse,
    PassengerUpdate,
)

__all__ = [
    "PassengerCreate",
    "PassengerMasked",
    "PassengerResponse",
    "PassengerUpdate",
    "create_passenger",
    "delete_passenger",
    "get_passenger_by_id",
    "get_passengers_for_user",
    "update_passenger",
]
