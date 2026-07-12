"""Hotel domain constants.

Constants used throughout the hotel domain, following the same patterns
as the flight domain for consistency.
"""

from datetime import timedelta

# Session Management
HOTEL_SESSION_EXPIRY_MINUTES = 20
"""FlightLogic hotel session expiry time (20 minutes per API docs)."""

HOTEL_SESSION_EXPIRY_DELTA = timedelta(minutes=HOTEL_SESSION_EXPIRY_MINUTES)
"""Session expiry as timedelta for MongoDB TTL."""

# Validation Constants
MIN_NIGHTS = 1
"""Minimum number of nights for a hotel stay."""

MAX_NIGHTS = 365
"""Maximum number of nights for a hotel stay (1 year)."""

MIN_ROOMS = 1
"""Minimum number of rooms for a search."""

MAX_ROOMS = 10
"""Maximum number of rooms for a single search."""

MIN_ADULTS_PER_ROOM = 1
"""Minimum number of adults per room."""

MAX_ADULTS_PER_ROOM = 8
"""Maximum number of adults per room."""

MAX_CHILDREN_PER_ROOM = 4
"""Maximum number of children per room."""

# Search Result Constraints
MIN_MAX_RESULT = 20
"""Minimum value for maxResult parameter (per FlightLogic API validation)."""

MAX_MAX_RESULT = 9999999999
"""Default and maximum value for maxResult in hotel search (request up to this many results)."""

DEFAULT_CURRENCY = "USD"
"""Default currency for hotel searches."""

# MongoDB Collections
HOTEL_SESSIONS_COLLECTION = "hotel_sessions"
"""Collection name for hotel search sessions."""

HOTEL_BOOKINGS_COLLECTION = "hotel_bookings"
"""Collection name for hotel bookings."""
