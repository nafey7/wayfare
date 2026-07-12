"""Timezone conversion utilities for flight bookings.

This module provides utilities to convert ticket time limits from departure city
local time to UTC using mwgg/Airports timezone data.

IMPORTANT: Only mwgg/Airports source is used for timezone conversion because
only it has timezone info. No other source has timezone info.
"""

import logging
from datetime import UTC, datetime

from app.domains.airport import airport_resolver

logger = logging.getLogger(__name__)


async def convert_ticket_time_limit_to_utc(
    local_time: datetime, departure_airport_iata: str
) -> datetime:
    """Convert ticket time limit from departure city local time to UTC.

    Uses ONLY mwgg/Airports source via AirportResolver to lookup airport timezone.
    mwgg is the ONLY source that provides timezone (tz field) for airports.

    Args:
        local_time: Naive datetime in departure city local time (from FlightLogic API)
        departure_airport_iata: IATA code of departure airport (e.g., "JFK", "LHR")

    Returns:
        Datetime in UTC. If airport not found or timezone missing, returns
        local_time as-is (assumes it's already UTC or falls back to UTC).

    Note:
        - IATA code is only used during conversion - not stored in database
        - If airport not found in mwgg or timezone missing, falls back to UTC
        - Handles DST transitions automatically via IANA timezone identifiers
    """
    logger.debug(
        f"Converting ticket time limit to UTC for airport {departure_airport_iata}. "
        f"Input: {local_time} (tzinfo: {local_time.tzinfo})"
    )

    if not departure_airport_iata:
        logger.warning(
            "No departure airport IATA code provided, assuming UTC for ticket_time_limit"
        )
        # If no timezone info, assume local_time is already UTC or use as-is
        return (
            local_time.replace(tzinfo=UTC) if local_time.tzinfo is None else local_time
        )

    try:
        # Get airport info from mwgg/Airports (ONLY source with timezone data)
        airport_info = await airport_resolver.get_airport_info(
            departure_airport_iata.upper()
        )

        if not airport_info:
            logger.warning(
                f"Airport {departure_airport_iata} not found in mwgg database, "
                "assuming UTC for ticket_time_limit"
            )
            return (
                local_time.replace(tzinfo=UTC)
                if local_time.tzinfo is None
                else local_time
            )

        # Extract timezone from mwgg data (tz field contains IANA timezone identifier)
        timezone_str = airport_info.get("tz")
        logger.debug(f"Airport {departure_airport_iata} timezone: {timezone_str}")
        if not timezone_str:
            logger.warning(
                f"Airport {departure_airport_iata} found but no timezone (tz) field, "
                "assuming UTC for ticket_time_limit"
            )
            return (
                local_time.replace(tzinfo=UTC)
                if local_time.tzinfo is None
                else local_time
            )

        # Use zoneinfo (Python 3.9+) for timezone conversion
        # Falls back to pytz if zoneinfo not available
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(timezone_str)
        except ImportError:
            # Fallback to pytz for older Python versions
            try:
                import pytz  # type: ignore[import-untyped]

                tz = pytz.timezone(timezone_str)
            except ImportError:
                logger.warning(
                    "Neither zoneinfo nor pytz available, assuming UTC for timezone conversion"
                )
                return (
                    local_time.replace(tzinfo=UTC)
                    if local_time.tzinfo is None
                    else local_time
                )

        # Convert local time to UTC
        # IMPORTANT: TktTimeLimit from FlightLogic is in departure city local time, but
        # _parse_datetime_string() incorrectly marks it as UTC. We need to strip the
        # timezone and treat it as local time for proper conversion.
        if local_time.tzinfo is None:
            # Naive datetime - assume it's in the departure city timezone
            logger.debug(
                f"Treating naive datetime {local_time} as local time in {timezone_str}"
            )
            if hasattr(tz, "localize"):
                # pytz timezone
                local_time_with_tz = tz.localize(local_time)
            else:
                # zoneinfo timezone
                local_time_with_tz = local_time.replace(tzinfo=tz)
        else:
            # If it already has timezone info, it's likely incorrectly marked as UTC
            # by _parse_datetime_string(). Strip the timezone and treat as local time.
            # This handles the case where FlightLogic returns naive datetime but
            # the parser incorrectly adds UTC timezone.
            logger.warning(
                f"Input datetime has timezone info ({local_time.tzinfo}), "
                f"but it should be naive. Stripping timezone and treating as {departure_airport_iata} "
                f"local time ({timezone_str}) for conversion."
            )
            naive_time = local_time.replace(tzinfo=None)
            if hasattr(tz, "localize"):
                # pytz timezone
                local_time_with_tz = tz.localize(naive_time)
            else:
                # zoneinfo timezone
                local_time_with_tz = naive_time.replace(tzinfo=tz)

        utc_time = local_time_with_tz.astimezone(UTC)
        logger.debug(
            f"Converted {departure_airport_iata} local time {local_time} ({timezone_str}) -> UTC {utc_time}"
        )
        return utc_time

    except Exception as e:
        logger.error(
            f"Error converting ticket_time_limit to UTC for airport {departure_airport_iata}: {e}",
            exc_info=True,
        )
        # Fallback: assume UTC
        fallback_result = (
            local_time.replace(tzinfo=UTC) if local_time.tzinfo is None else local_time
        )
        logger.warning(
            f"Using fallback: {local_time} -> {fallback_result} (assumed UTC)"
        )
        return fallback_result
