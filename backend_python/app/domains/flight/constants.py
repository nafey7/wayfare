"""Flight domain constants.

Domain-specific constants for flight operations and bookings.
"""

from typing import Final

# ==============================================================================
# REQUIRED BOOKING FIELDS
# ==============================================================================

# Note: Required booking fields are determined dynamically by the FlightLogic API
# The API returns RequiredFieldsToBook and IsPassportMandatory for each flight
# See RequiredBookingField enum in enums.py for possible values

# ==============================================================================
# FLIGHT SEARCH LIMITS
# ==============================================================================

MAX_PASSENGERS_PER_BOOKING: Final[int] = 9
MAX_INFANTS_PER_ADULT: Final[int] = 1
MIN_CONNECTION_TIME_MINUTES: Final[int] = 45
MAX_CONNECTION_TIME_HOURS: Final[int] = 24

# ==============================================================================
# DEFAULT TIME LIMITS (Fallbacks only - actual values come from API)
# ==============================================================================

# These are ONLY fallback values when API doesn't provide them
# Actual values should come from:
# - TicketTimeLimit from FlightLogic booking response
# - Airline-specific rules from fare conditions
DEFAULT_TICKET_TIME_LIMIT_HOURS: Final[int] = 24  # Fallback only
DEFAULT_AIRPORT_ARRIVAL_TIME_HOURS: Final[int] = 2  # General recommendation
