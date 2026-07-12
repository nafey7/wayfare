"""Flight search result filtering utilities.

This module provides a modular and clean approach to filtering flight search results
after receiving them from the FlightLogic API. All filters are applied post-API.

For comprehensive documentation on available filters, payload structure, and filter
application logic, see FILTERS_DOCUMENTATION.md in this directory.
"""

import logging
from datetime import datetime
from typing import Any

from app.domains.flight.schemas import (
    FareItinerary,
    FlightLeg,
    FlightSearchFilters,
    FlightSearchResponse,
    LegFilter,
    TimeWindow,
)

logger = logging.getLogger(__name__)


def filter_flight_results(
    response: FlightSearchResponse,
    filters: FlightSearchFilters | None,
    requested_origin_code: str | None = None,
    requested_destination_code: str | None = None,
) -> FlightSearchResponse:
    """Filter flight search results based on provided filters.

    This function applies all filters to the flight search results after receiving
    them from the FlightLogic API. Filters are applied in the following order:
    1. Global filters (price, refundability, stops, airlines, etc.)
    2. City-wise search filters (origin/destination airport matching)
    3. Leg-specific filters (time windows, duration, layover airports)

    Args:
        response: Flight search response from FlightLogic API
        filters: Filter configuration to apply
        requested_origin_code: Requested origin airport IATA code (for city-wise filtering)
        requested_destination_code: Requested destination airport IATA code (for city-wise filtering)

    Returns:
        Filtered FlightSearchResponse with only matching flights
    """
    if not filters:
        # No filters provided - return response as-is
        return response

    initial_outbound_count = len(response.fare_itineraries)
    initial_inbound_count = len(response.inbound_fare_itineraries or [])

    logger.debug(
        "Applying global filters",
        extra={
            "has_filters": filters is not None,
            "min_price": filters.min_price,
            "max_price": filters.max_price,
            "is_refundable": filters.is_refundable,
            "carrier": filters.carrier,
            "max_stops": filters.max_stops,
            "operating_airlines": filters.operating_airlines,
        },
    )

    # Filter outbound flights (supports multi-city: FareItinerary can have multiple legs)
    # For multi-city flights, a single FareItinerary may contain legs: 0, 1, 2, 3, etc.
    # For round trips, a FareItinerary may contain both outbound (leg 0) and inbound (leg 1) legs.
    # We check leg_index=0 for city-wise and leg-specific filters (primary route)
    # The max_stops filter checks ALL legs in the FareItinerary (see _passes_global_filters)
    filtered_outbound = []
    for fare_itinerary in response.fare_itineraries:
        # Check outbound leg (leg_index=0)
        if not _should_keep_fare_itinerary(
            fare_itinerary,
            filters,
            structural_leg_index=0,
            semantic_leg_index=0,  # Outbound leg in filter payload
            requested_origin_code=requested_origin_code,
            requested_destination_code=requested_destination_code,
        ):
            continue  # Skip if outbound leg doesn't pass filters

        # For round trips: also check inbound leg (leg_index=1) if it exists in this FareItinerary
        # This handles cases where both legs are in the same FareItinerary (not in inbound_fare_itineraries)
        if len(fare_itinerary.flight_legs) > 1 and not _should_keep_fare_itinerary(
            fare_itinerary,
            filters,
            structural_leg_index=1,  # Second leg in array
            semantic_leg_index=1,  # Inbound leg in filter payload
            requested_origin_code=requested_destination_code,  # Swapped for inbound
            requested_destination_code=requested_origin_code,  # Swapped for inbound
        ):
            continue  # Skip if inbound leg doesn't pass filters

        filtered_outbound.append(fare_itinerary)

    response.fare_itineraries = filtered_outbound

    # Filter inbound flights for round trips
    # Note: inbound_fare_itineraries are separate FareItinerary objects.
    # They may contain only the inbound leg at index 0, or both legs (outbound at 0, inbound at 1).
    # IMPORTANT: We need to distinguish between:
    # - Structural leg_index: actual array position in fare_itinerary.flight_legs (0 or 1)
    # - Semantic leg_index: leg_index in filter payload (0=outbound, 1=inbound, 2+=multi-city)
    # For inbound, structural index may be 0 or 1, but semantic index is always 1.
    if response.inbound_fare_itineraries:
        filtered_inbound = []
        for fare_itinerary in response.inbound_fare_itineraries:
            # Determine the structural leg index (actual array position)
            # If there are 2+ legs, use index 1 (inbound), otherwise use index 0
            structural_leg_index = 1 if len(fare_itinerary.flight_legs) > 1 else 0
            # Semantic leg_index for filter lookup is always 1 for inbound flights
            semantic_leg_index = 1

            logger.debug(
                "Filtering inbound fare itinerary",
                extra={
                    "num_legs": len(fare_itinerary.flight_legs),
                    "structural_leg_index": structural_leg_index,
                    "semantic_leg_index": semantic_leg_index,
                    "max_stops_filter": filters.max_stops if filters else None,
                },
            )

            if _should_keep_fare_itinerary(
                fare_itinerary,
                filters,
                structural_leg_index=structural_leg_index,
                semantic_leg_index=semantic_leg_index,
                requested_origin_code=requested_destination_code,  # Swapped for inbound
                requested_destination_code=requested_origin_code,  # Swapped for inbound
            ):
                filtered_inbound.append(fare_itinerary)
        response.inbound_fare_itineraries = filtered_inbound

    final_outbound_count = len(response.fare_itineraries)
    final_inbound_count = len(response.inbound_fare_itineraries or [])

    logger.debug(
        f"🔍 Filtering results: outbound {initial_outbound_count} -> {final_outbound_count}, "
        f"inbound {initial_inbound_count} -> {final_inbound_count}"
    )

    return response


def _should_keep_fare_itinerary(
    fare_itinerary: FareItinerary,
    filters: FlightSearchFilters,
    structural_leg_index: int | None = None,
    semantic_leg_index: int | None = None,
    leg_index: int | None = None,  # For backward compatibility
    requested_origin_code: str | None = None,
    requested_destination_code: str | None = None,
) -> bool:
    """Check if a fare itinerary should be kept based on filters.

    Supports multi-city flights: a FareItinerary can have multiple legs (0, 1, 2, 3, etc.).
    - max_stops filter checks ALL legs in the FareItinerary
    - City-wise and leg-specific filters check the leg at structural_leg_index

    Args:
        fare_itinerary: Fare itinerary to check (may contain multiple legs for multi-city)
        filters: Filter configuration
        structural_leg_index: Actual array index in fare_itinerary.flight_legs (for accessing the leg)
        semantic_leg_index: Semantic leg index in filter payload (0=outbound, 1=inbound, 2+=multi-city, for filter lookup)
        leg_index: Legacy parameter for backward compatibility (used as both structural and semantic)
        requested_origin_code: Requested origin airport code
        requested_destination_code: Requested destination airport code

    Returns:
        True if itinerary should be kept, False otherwise
    """
    if not fare_itinerary.flight_legs:
        return False

    # Backward compatibility: if only leg_index is provided, use it for both
    if structural_leg_index is None and semantic_leg_index is None:
        if leg_index is not None:
            structural_leg_index = leg_index
            semantic_leg_index = leg_index
        else:
            return False

    # Type narrowing: at this point, both indices must be set
    if structural_leg_index is None or semantic_leg_index is None:
        return False

    # Get the leg using structural index (actual array position)
    if structural_leg_index >= len(fare_itinerary.flight_legs):
        return False
    leg = fare_itinerary.flight_legs[structural_leg_index]
    if not leg or not leg.flight_segments:
        return False

    # Apply global filters first
    # Note: max_stops filter checks ALL legs in the FareItinerary (supports multi-city)
    if not _passes_global_filters(fare_itinerary, filters):
        return False

    # Get leg-specific filter for city-wise search check
    leg_filter = _get_leg_filter(filters, semantic_leg_index)

    # Determine if this is an inbound leg (semantic_leg_index == 1 for round trips)
    is_inbound = semantic_leg_index == 1

    # Apply city-wise search filters (checks leg-specific first, then falls back to global)
    if not _passes_city_wise_filters(
        leg,
        filters,
        leg_filter,
        requested_origin_code,
        requested_destination_code,
        is_inbound=is_inbound,
    ):
        return False

    # Apply other leg-specific filters
    return leg_filter is None or _passes_leg_filters(leg, leg_filter)


def _passes_global_filters(
    fare_itinerary: FareItinerary,
    filters: FlightSearchFilters,
) -> bool:
    """Check if fare itinerary passes global filters.

    Supports multi-city flights: checks ALL legs in the FareItinerary for filters
    like max_stops (each leg must individually pass).

    Args:
        fare_itinerary: Fare itinerary to check (may contain multiple legs for multi-city)
        filters: Filter configuration

    Returns:
        True if passes all global filters, False otherwise
    """
    # Price range filter
    if filters.min_price is not None or filters.max_price is not None:
        if not fare_itinerary.pricing or not fare_itinerary.pricing.fare_totals:
            return False
        total_fare = fare_itinerary.pricing.fare_totals.total_fare
        if not total_fare:
            return False
        price = float(total_fare.amount)
        if filters.min_price is not None and price < filters.min_price:
            logger.debug(
                "Filtered out by min_price",
                extra={"price": price, "min_price": filters.min_price},
            )
            return False
        if filters.max_price is not None and price > filters.max_price:
            logger.debug(
                "Filtered out by max_price",
                extra={"price": price, "max_price": filters.max_price},
            )
            return False

    # Refundability filter
    if filters.is_refundable is not None:
        if not fare_itinerary.pricing:
            return False
        if fare_itinerary.pricing.is_refundable != filters.is_refundable:
            logger.debug(
                "Filtered out by refundability",
                extra={
                    "is_refundable": fare_itinerary.pricing.is_refundable,
                    "expected": filters.is_refundable,
                },
            )
            return False

    # Carrier filter (GDS or LCC)
    # GDS = "Private" or "Public" fare types
    # LCC = "WebFare" fare type
    # Note: carrier field is validated by Pydantic schema (Literal["GDS", "LCC"])
    if filters.carrier is not None:
        if not fare_itinerary.pricing:
            return False
        # Map FareType enum to string for comparison
        fare_type_str = (
            fare_itinerary.pricing.fare_type.value
            if hasattr(fare_itinerary.pricing.fare_type, "value")
            else str(fare_itinerary.pricing.fare_type)
        )
        # Map fare_type to carrier type
        # GDS: "Private" or "Public"
        # LCC: "WebFare"
        is_gds = fare_type_str in ("Private", "Public")
        is_lcc = fare_type_str == "WebFare"

        # Check if the carrier filter matches
        carrier_upper = filters.carrier.upper()
        if carrier_upper == "GDS" and not is_gds:
            logger.debug(
                "Filtered out by carrier",
                extra={
                    "fare_type": fare_type_str,
                    "carrier": carrier_upper,
                    "is_gds": is_gds,
                },
            )
            return False
        if carrier_upper == "LCC" and not is_lcc:
            logger.debug(
                "Filtered out by carrier",
                extra={
                    "fare_type": fare_type_str,
                    "carrier": carrier_upper,
                    "is_lcc": is_lcc,
                },
            )
            return False

    # Max stops filter (check ALL legs individually - supports multi-city flights)
    # For multi-city flights, a FareItinerary can have multiple legs (0, 1, 2, 3, etc.)
    # ALL legs must individually pass the max_stops filter
    if filters.max_stops is not None:
        # Always check all legs in the fare itinerary (not just the specific leg)
        # This ensures multi-city flights are properly filtered
        for idx, leg_to_check in enumerate(fare_itinerary.flight_legs):
            if leg_to_check.total_stops > filters.max_stops:
                logger.debug(
                    "Filtered out by max_stops",
                    extra={
                        "leg_index": idx,
                        "leg_stops": leg_to_check.total_stops,
                        "max_stops": filters.max_stops,
                        "total_legs": len(fare_itinerary.flight_legs),
                    },
                )
                return False

    # Operating airline filter
    # Matches flights where ANY segment is operated by an airline in the filter list
    # Only matches by airline name (case-insensitive), not by IATA code
    if filters.operating_airlines is not None:
        if not filters.operating_airlines:
            # Empty list means no filter applied
            return True

        # Check if any segment has matching operating airline
        found_match = False
        for flight_leg in fare_itinerary.flight_legs:
            for segment in flight_leg.flight_segments:
                if segment.operating_airline:
                    airline_name = segment.operating_airline.airline_name or ""
                    # Match by airline name only (case-insensitive)
                    for filter_airline in filters.operating_airlines:
                        if airline_name.upper() == filter_airline.upper():
                            found_match = True
                            break
                    if found_match:
                        break
            if found_match:
                break
        if not found_match:
            logger.debug(
                "Filtered out by operating_airlines",
                extra={
                    "operating_airlines": filters.operating_airlines,
                    "checked_all_segments": True,
                },
            )
            return False

    return True


def _passes_city_wise_filters(
    leg: FlightLeg,
    filters: FlightSearchFilters,
    leg_filter: LegFilter | None,
    requested_origin_code: str | None,
    requested_destination_code: str | None,
    is_inbound: bool = False,
) -> bool:
    """Check if leg passes city-wise search filters.

    Checks leg-specific city_wise_search first, then falls back to global filters
    for backward compatibility.

    For inbound legs, the filter flags are swapped:
    - city_wise_search_origin applies to inbound destination (original origin)
    - city_wise_search_destination applies to inbound origin (original destination)

    Args:
        leg: Flight leg to check
        filters: Filter configuration
        leg_filter: Leg-specific filter (may contain city_wise_search)
        requested_origin_code: Requested origin airport code
        requested_destination_code: Requested destination airport code
        is_inbound: Whether this is an inbound leg (for round trips)

    Returns:
        True if passes city-wise filters, False otherwise
    """
    if not leg.flight_segments:
        return False

    # Get origin from first segment
    flight_origin_code = leg.flight_segments[0].departure_airport.iata_code

    # Get destination from last segment
    flight_destination_code = leg.flight_segments[-1].arrival_airport.iata_code

    # Determine city-wise search setting: leg-specific first, then global fallback
    # If leg_filter has city_wise_search set, use it (applies to both origin and destination)
    # Otherwise, fall back to global filters (separate origin/destination flags)
    if leg_filter is not None and leg_filter.city_wise_search is not None:
        # Use leg-specific city_wise_search (applies to both origin and destination)
        city_wise_enabled = leg_filter.city_wise_search
        if not city_wise_enabled:
            # Exact match required for both origin and destination
            if requested_origin_code and flight_origin_code != requested_origin_code:
                logger.debug(
                    "Filtered out by leg-specific city_wise_search (origin)",
                    extra={
                        "leg_index": leg_filter.leg_index,
                        "flight_origin_code": flight_origin_code,
                        "requested_origin_code": requested_origin_code,
                    },
                )
                return False
            if (
                requested_destination_code
                and flight_destination_code != requested_destination_code
            ):
                logger.debug(
                    "Filtered out by leg-specific city_wise_search (destination)",
                    extra={
                        "leg_index": leg_filter.leg_index,
                        "flight_destination_code": flight_destination_code,
                        "requested_destination_code": requested_destination_code,
                    },
                )
                return False
    # Fall back to global filters (backward compatibility)
    # For inbound legs, swap which filter flag applies to which check:
    # - Inbound origin check uses city_wise_search_destination (inbound origin = original destination)
    # - Inbound destination check uses city_wise_search_origin (inbound destination = original origin)
    elif is_inbound:
        # Check inbound origin (original destination) - use city_wise_search_destination flag
        if (
            requested_origin_code
            and not filters.city_wise_search_destination
            and flight_origin_code != requested_origin_code
        ):
            logger.debug(
                "Filtered out by global city_wise_search_destination (inbound origin)",
                extra={
                    "flight_origin_code": flight_origin_code,
                    "requested_origin_code": requested_origin_code,
                },
            )
            return False

        # Check inbound destination (original origin) - use city_wise_search_origin flag
        if (
            requested_destination_code
            and not filters.city_wise_search_origin
            and flight_destination_code != requested_destination_code
        ):
            logger.debug(
                "Filtered out by global city_wise_search_origin (inbound destination)",
                extra={
                    "flight_destination_code": flight_destination_code,
                    "requested_destination_code": requested_destination_code,
                },
            )
            return False
    else:
        # Outbound leg: use flags directly
        # Filter: Keep only flights where origin matches requested origin (if flag is False/None)
        if (
            requested_origin_code
            and not filters.city_wise_search_origin
            and flight_origin_code != requested_origin_code
        ):
            logger.debug(
                "Filtered out by global city_wise_search_origin",
                extra={
                    "flight_origin_code": flight_origin_code,
                    "requested_origin_code": requested_origin_code,
                },
            )
            return False

        # Filter: Keep only flights where destination matches requested destination (if flag is False/None)
        if (
            requested_destination_code
            and not filters.city_wise_search_destination
            and flight_destination_code != requested_destination_code
        ):
            logger.debug(
                "Filtered out by global city_wise_search_destination",
                extra={
                    "flight_destination_code": flight_destination_code,
                    "requested_destination_code": requested_destination_code,
                },
            )
            return False

    return True


def _get_leg_filter(filters: FlightSearchFilters, leg_index: int) -> LegFilter | None:
    """Get leg-specific filter for the given leg index.

    Args:
        filters: Filter configuration
        leg_index: Leg index (0 for outbound, 1 for inbound)

    Returns:
        LegFilter if found, None otherwise
    """
    if not filters.journey_filters:
        return None

    for leg_filter in filters.journey_filters:
        if leg_filter.leg_index == leg_index:
            return leg_filter

    return None


def _passes_leg_filters(leg: FlightLeg, leg_filter: LegFilter) -> bool:
    """Check if leg passes leg-specific filters.

    Args:
        leg: Flight leg to check
        leg_filter: Leg-specific filter configuration

    Returns:
        True if passes all leg filters, False otherwise
    """
    if not leg.flight_segments:
        return False

    # Departure time window filter (first segment rule)
    if leg_filter.departure_window:
        first_segment = leg.flight_segments[0]
        if not _passes_time_window(
            first_segment.departure_datetime, leg_filter.departure_window
        ):
            return False

    # Arrival time window filter (last segment rule)
    if leg_filter.arrival_window:
        last_segment = leg.flight_segments[-1]
        if not _passes_time_window(
            last_segment.arrival_datetime, leg_filter.arrival_window
        ):
            return False

    # Max duration filter
    if leg_filter.max_duration_minutes is not None:
        total_duration = _calculate_leg_duration(leg)
        if total_duration > leg_filter.max_duration_minutes:
            return False

    # Layover airport filters
    if (
        leg_filter.excluded_layover_airports or leg_filter.allowed_layover_airports
    ) and not _passes_layover_filters(leg, leg_filter):
        logger.debug(
            "Filtered out by layover airports",
            extra={
                "excluded": leg_filter.excluded_layover_airports,
                "allowed": leg_filter.allowed_layover_airports,
            },
        )
        return False

    return True


def _passes_time_window(datetime_obj: Any, time_window: TimeWindow) -> bool:
    """Check if datetime falls within time window.

    Args:
        datetime_obj: DateTime object to check (can be DateTime wrapper or datetime)
        time_window: Time window (HH:mm format)

    Returns:
        True if datetime is within window, False otherwise
    """
    # Extract time from datetime
    dt = datetime_obj.value if hasattr(datetime_obj, "value") else datetime_obj

    if isinstance(dt, str):
        # Parse ISO format string
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

    time_str = dt.strftime("%H:%M")

    # Handle midnight-crossing windows (e.g., night: 23:00-05:00)
    if time_window.min > time_window.max:
        # Time window crosses midnight
        return time_str >= time_window.min or time_str <= time_window.max
    # Normal time window within same day
    return time_window.min <= time_str <= time_window.max


def _calculate_leg_duration(leg: FlightLeg) -> int:
    """Calculate total leg duration in minutes.

    Matches frontend calculation: Flight Duration + Layover Time = Total Travel Time

    Args:
        leg: Flight leg

    Returns:
        Duration in minutes (includes flight time + layover time)
    """
    if not leg.flight_segments:
        return 0

    # Step 1: Calculate flight duration (sum of all segment flight times)
    leg_minutes = 0
    for segment in leg.flight_segments:
        if (
            segment.flight_duration
            and hasattr(segment.flight_duration, "total_minutes")
            and segment.flight_duration.total_minutes
        ):
            leg_minutes += segment.flight_duration.total_minutes

    # Step 2: Calculate total layover time between segments
    total_layover_minutes: float = 0.0
    for i in range(len(leg.flight_segments) - 1):
        current_segment = leg.flight_segments[i]
        next_segment = leg.flight_segments[i + 1]

        # Extract arrival datetime from current segment
        current_arr_raw = current_segment.arrival_datetime
        current_arr: datetime | None = None
        current_arr_value: Any = current_arr_raw
        if hasattr(current_arr_raw, "value"):
            current_arr_value = current_arr_raw.value
        if isinstance(current_arr_value, str):
            current_arr = datetime.fromisoformat(
                current_arr_value.replace("Z", "+00:00")
            )
        elif isinstance(current_arr_value, datetime):
            current_arr = current_arr_value

        # Extract departure datetime from next segment
        next_dep_raw = next_segment.departure_datetime
        next_dep: datetime | None = None
        next_dep_value: Any = next_dep_raw
        if hasattr(next_dep_raw, "value"):
            next_dep_value = next_dep_raw.value
        if isinstance(next_dep_value, str):
            next_dep = datetime.fromisoformat(next_dep_value.replace("Z", "+00:00"))
        elif isinstance(next_dep_value, datetime):
            next_dep = next_dep_value

        # Calculate layover time if both datetimes are valid
        if isinstance(current_arr, datetime) and isinstance(next_dep, datetime):
            layover_mins = (next_dep - current_arr).total_seconds() / 60
            if layover_mins > 0:  # Only add positive layover times
                total_layover_minutes += layover_mins

    # Step 3: Total time = Flight Duration + Layover Time
    total_time_minutes = leg_minutes + total_layover_minutes
    return int(total_time_minutes)


def _passes_layover_filters(leg: FlightLeg, leg_filter: LegFilter) -> bool:
    """Check if leg passes layover airport filters.

    Args:
        leg: Flight leg to check
        leg_filter: Leg-specific filter configuration

    Returns:
        True if passes layover filters, False otherwise
    """
    is_direct = len(leg.flight_segments) <= 1

    # Direct flights fail if allowed_layover_airports is specified
    # (user wants flights through specific airports, direct flights don't go through any)
    if leg_filter.allowed_layover_airports and is_direct:
        logger.debug(
            "Direct flight filtered out by allowed_layover_airports",
            extra={
                "allowed_layover_airports": leg_filter.allowed_layover_airports,
                "reason": "direct flights have no layovers",
            },
        )
        return False

    if is_direct:
        # Direct flights pass excluded_layover_airports check (no layovers to exclude)
        return True

    # Get layover airports (departure airports excluding the first segment)
    layover_airports = []
    for i in range(1, len(leg.flight_segments)):
        layover_airport = leg.flight_segments[i].departure_airport.iata_code
        layover_airports.append(layover_airport)

    # Check excluded layover airports
    if leg_filter.excluded_layover_airports:
        for excluded in leg_filter.excluded_layover_airports:
            if excluded.upper() in [airport.upper() for airport in layover_airports]:
                return False

    # Check allowed layover airports
    if leg_filter.allowed_layover_airports and layover_airports:
        # At least one layover must be in allowed list
        allowed_upper = [
            airport.upper() for airport in leg_filter.allowed_layover_airports
        ]
        if not any(airport.upper() in allowed_upper for airport in layover_airports):
            return False

    return True
