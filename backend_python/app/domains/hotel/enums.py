"""Hotel domain enumerations.

This module defines all enum types used in the hotel domain, following the same
patterns as the flight domain for consistency across the codebase.
"""

from enum import StrEnum


class HotelFareType(StrEnum):
    """Hotel fare/rate types.

    Indicates whether a booking is refundable or non-refundable.
    """

    REFUNDABLE = "Refundable"
    NON_REFUNDABLE = "Non-Refundable"


class PropertyType(StrEnum):
    """Hotel property types.

    Different types of accommodation properties available.
    """

    HOTEL = "hotel"
    RESORT = "resort"
    APARTMENT = "apartment"
    VILLA = "villa"
    HOSTEL = "hostel"
    GUESTHOUSE = "guest house"
    MOTEL = "motel"
    BED_AND_BREAKFAST = "bed and breakfast"
    VACATION_RENTAL = "vacation rental"


class RoomType(StrEnum):
    """Room types/categories.

    Common room configurations available in hotels.
    """

    SINGLE = "Single"
    DOUBLE = "Double"
    TWIN = "Twin"
    TRIPLE = "Triple"
    QUAD = "Quad"
    SUITE = "Suite"
    DELUXE = "Deluxe"
    STANDARD = "Standard"
    SUPERIOR = "Superior"
    EXECUTIVE = "Executive"


class MealPlan(StrEnum):
    """Meal plan types included with room rate.

    Different meal arrangements that may be included in the booking.
    """

    ROOM_ONLY = "Room only"
    BREAKFAST_INCLUDED = "Breakfast included"
    HALF_BOARD = "Half board"
    FULL_BOARD = "Full board"
    ALL_INCLUSIVE = "All inclusive"


class BookingStatus(StrEnum):
    """Booking status values.

    Lifecycle states of a hotel booking.
    """

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class CancellationPolicy(StrEnum):
    """Cancellation policy types.

    Common cancellation policy patterns.
    """

    FREE_CANCELLATION = "Free cancellation"
    NON_REFUNDABLE = "Non-refundable"
    PARTIAL_REFUND = "Partial refund"
    CONDITIONAL = "Conditional cancellation"


class DistanceUnit(StrEnum):
    """Units for distance measurements.

    Used for hotel distance from city center or landmarks.
    """

    KM = "KM"
    MI = "MI"
    METERS = "M"
