"""Bookings Log domain package.

This domain manages the complete booking lifecycle log - tracking everything from initial interest to final transaction:

Booking Journey Stages:
- 🤔 Interest: "User interested in Bali vacation"
- 🔍 Search: Flight searches, hotel lookups, price comparisons
- 📝 Draft: Incomplete bookings, saved preferences, wishlists
- 💳 Booking: Confirmed flights, hotels, activities, payments
- 📧 Processing: Confirmations, emails, ticket generation
- 🔄 Changes: Modifications, cancellations, refunds
- ⚠️ Issues: Failures, errors, support interactions

Complete audit trail of every booking process.
"""

from .reference_generator import VoyaReferenceGenerator
from .repository import BookingRepository
from .schemas import (
    BookingEventResponse,
    CreateBookingEventRequest,
    FlightContent,
    UpdateBookingEventRequest,
)
from .service import BookingService

__all__ = [
    "BookingEventResponse",
    "BookingRepository",
    "BookingService",
    "CreateBookingEventRequest",
    "FlightContent",
    "UpdateBookingEventRequest",
    "VoyaReferenceGenerator",
]
