"""Trip information extraction tool for itinerary planning.

This tool allows the Planning Agent to save extracted trip information to state.
Includes automatic date parsing for natural language dates.
"""

import json
import logging
import unicodedata
from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _normalize_city_name(name: str) -> str:
    """Strip country suffix and diacritics for API compatibility.

    Examples: "Cancún, Mexico" → "Cancun", "São Paulo, Brazil" → "Sao Paulo"
    """
    # Strip country suffix (e.g. "Cancún, Mexico" → "Cancún")
    name = name.split(",")[0].strip()
    # Strip diacritics (e.g. "Cancún" → "Cancun")
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


@tool
async def update_trip_info(
    origin: str | None = None,
    destination: str | None = None,
    origin_iata: str | None = None,
    destination_iata: str | None = None,
    origin_name: str | None = None,
    destination_name: str | None = None,
    departure_date: str | None = None,
    return_date: str | None = None,
    adults: int | None = None,
    children: int | None = None,
    infants: int | None = None,
    interests: list[str] | None = None,
    trip_duration_days: int | None = None,
    existing_departure_date: str | None = None,
) -> str:
    """Save extracted trip information to state.

    Use this tool to save trip details extracted from user messages.
    Automatically parses natural language dates to YYYY-MM-DD format.

    Args:
        origin: Origin city/location (e.g., "Paris", "New York")
        destination: Destination city/location (e.g., "Chamonix", "London")
        origin_iata: Origin airport IATA code (e.g., "CDG", "JFK") - resolved from origin city
        destination_iata: Destination airport IATA code (e.g., "LHR", "LAX") - resolved from destination city
        origin_name: Origin airport full name (e.g., "Paris Charles de Gaulle")
        destination_name: Destination airport full name (e.g., "London Heathrow")
        departure_date: Departure date - accepts natural language (e.g., "Jan 15", "tomorrow") or YYYY-MM-DD
        return_date: Return date - accepts natural language or YYYY-MM-DD (optional, for round trips)
        adults: Number of adult travelers (default: 1)
        children: Number of child travelers (default: 0)
        infants: Number of infant travelers under 2 years old (default: 0)
        interests: List of trip interests (e.g., ["skiing", "mountains", "culture"])
        trip_duration_days: Trip duration from parse_dates (e.g., 5). When departure_date is
            known but return_date is missing, return_date is auto-derived as departure + duration.
        existing_departure_date: The previously-collected departure_date (if any), passed as
            context so date parsing can apply state-aware swap-to-return logic. When provided
            AND the new departure_date parses to a value before existing_departure_date,
            the existing departure is preserved (NOT overwritten) and an error is returned —
            this prevents silent overwriting from ambiguous inputs like option-number selections.

    State-aware contract (#1014):
        - Caller passes only ``departure_date`` (no return) + ``existing_departure_date``:
          state-aware swap/preserve applies. New date > existing → swap to return.
          New date < existing → preserve existing, ``status="ambiguous_date"``.
        - Caller passes ``return_date`` only: validated against existing or new departure;
          if return ≤ departure → ``status="invalid_return_date"`` (not stored).
        - Caller passes BOTH ``departure_date`` and ``return_date`` in the same call:
          this is treated as an explicit "change whole trip" intent.
          ``existing_departure_date`` is NOT forwarded to parse_dates so the new range is
          accepted as-is. Required to support e.g. "15 may to 5 june" replacing an
          earlier proposed range.

    Returns:
        Dictionary with saved trip information:
        {
            "status": "success",
            "origin": str,
            "destination": str,
            "departure_date": str,
            "return_date": str | None,
            "adults": int,
            "children": int,
            "interests": list[str],
            "message": str
        }

    Example:
        >>> result = await update_trip_info(
        ...     origin="Paris",
        ...     destination="Chamonix",
        ...     departure_date="2025-01-15",
        ...     adults=2,
        ...     interests=["skiing", "mountains"]
        ... )
        >>> result["origin"]  # "Paris"
    """
    # Build result dictionary with provided values
    result: dict[str, Any] = {
        "status": "success",
        "message": "Trip information saved successfully",
    }

    # Only include fields that were provided (not None)
    if origin is not None:
        result["origin"] = _normalize_city_name(origin.strip())
    if destination is not None:
        result["destination"] = _normalize_city_name(destination.strip())

    # Airport IATA codes (resolved by Planning Agent using resolve_airport tool)
    if origin_iata is not None:
        result["origin_iata"] = origin_iata.strip().upper()
    if destination_iata is not None:
        result["destination_iata"] = destination_iata.strip().upper()
    if origin_name is not None:
        result["origin_name"] = origin_name.strip()
    if destination_name is not None:
        result["destination_name"] = destination_name.strip()

    # Parse dates (handles both natural language and YYYY-MM-DD)
    if departure_date is not None:
        from app.ai.graph.tools.dates import parse_dates

        # Pass existing_departure_date so state-aware swap-to-return logic applies.
        # Without this, "May 15" said after dep=May 18 was already collected would
        # silently overwrite the departure (Session 2 bug, #1014).
        #
        # EXCEPTION: when the agent passes BOTH a new departure_date AND a new
        # return_date in the SAME call, that's an explicit "change the whole
        # trip" intent (e.g. user said "15 may to 5 june"). The existing
        # departure must NOT shadow this — drop the state context so the new
        # range is accepted as-is.
        parse_args: dict[str, Any] = {"text": departure_date}
        replacing_full_range = return_date is not None
        if existing_departure_date and not replacing_full_range:
            parse_args["departure_date"] = existing_departure_date
        parse_result = await parse_dates.ainvoke(parse_args)

        # If validator rejected the new date as ambiguous (parsed < existing),
        # the result preserves existing_departure and surfaces an error.
        # Propagate the error/instruction back to the agent.
        if parse_result.get("error") and existing_departure_date:
            logger.info(
                "update_trip_info: preserving existing departure_date=%s due to ambiguous input '%s'",
                existing_departure_date,
                departure_date,
            )
            result["departure_date"] = existing_departure_date
            result["status"] = "ambiguous_date"
            result["message"] = parse_result["error"]
            result["instruction"] = parse_result.get(
                "instruction", "Ask the user to clarify the date."
            )
            return json.dumps(result)

        parsed_departure = (
            parse_result.get("departure_date")
            if not parse_result.get("error")
            else None
        )
        # Also pick up return_date if the swap-to-return logic fired in parse_dates.
        parsed_return_from_swap = parse_result.get("return_date")

        if parsed_departure:
            result["departure_date"] = parsed_departure
            logger.info(
                f"Parsed departure date: '{departure_date}' → '{parsed_departure}'"
            )

            # Check if it's a date range (e.g., "May holiday season") OR if the
            # state-aware swap fired (existing_departure preserved + new date
            # interpreted as return).
            if parse_result.get("is_range") and parsed_return_from_swap:
                result["return_date"] = parsed_return_from_swap
                logger.info(
                    f"Also parsed return date from range/swap: '{departure_date}' → '{parsed_return_from_swap}'"
                )
        else:
            logger.warning(f"Could not parse departure date: '{departure_date}'")
            result["departure_date"] = departure_date  # Keep original if parsing fails

    if return_date is not None:
        from app.ai.graph.tools.dates import parse_dates

        parse_result = await parse_dates.ainvoke({"text": return_date})
        parsed_return = (
            parse_result.get("departure_date")
            if not parse_result.get("error")
            else None
        )

        # Guard: reject return_date that lands on or before departure_date.
        # Without this, the agent can "rescue" a rejected ambiguous departure
        # (e.g. "15-5" → May 15 preserved as dep=May 18) by silently reassigning
        # the same date to return_date, producing an impossible May 18 → May 15
        # trip. Fixes #1014 (Session 2 spillover).
        anchor_dep = result.get("departure_date") or existing_departure_date
        if parsed_return and anchor_dep:
            try:
                dep_d = datetime.strptime(anchor_dep, "%Y-%m-%d").date()
                ret_d = datetime.strptime(parsed_return, "%Y-%m-%d").date()
                if ret_d <= dep_d:
                    logger.info(
                        "update_trip_info: rejecting return_date=%s (not after departure=%s)",
                        parsed_return,
                        anchor_dep,
                    )
                    result["status"] = "invalid_return_date"
                    result["message"] = (
                        f"Return date ({parsed_return}) must be after departure "
                        f"({anchor_dep})."
                    )
                    result["instruction"] = (
                        f"Return date '{parsed_return}' is not after departure_date "
                        f"'{anchor_dep}'. Do NOT store it. Ask the user explicitly for "
                        f"a return date AFTER {anchor_dep}, OR confirm whether they "
                        f"meant to CHANGE the departure date to '{parsed_return}'."
                    )
                    return json.dumps(result)
            except (ValueError, TypeError):
                pass

        if parsed_return:
            result["return_date"] = parsed_return
            logger.info(f"Parsed return date: '{return_date}' → '{parsed_return}'")

            # Check if it's a date range (edge case: agent gave range for return_date)
            # E.g., "return May 1-5" → use end date
            if parse_result.get("is_range") and parse_result.get("return_date"):
                parsed_end = parse_result.get("return_date")
                result["return_date"] = parsed_end
                logger.info(
                    f"Agent provided range for return, using end date: '{parsed_end}'"
                )
        else:
            logger.warning(f"Could not parse return date: '{return_date}'")
            result["return_date"] = return_date  # Keep original if parsing fails

    if adults is not None:
        result["adults"] = adults
    if children is not None:
        result["children"] = children
    if infants is not None:
        result["infants"] = infants
    if interests is not None:
        result["interests"] = interests
    if trip_duration_days is not None:
        result["trip_duration_days"] = trip_duration_days

    logger.info(
        f"Trip info updated: origin={origin}, destination={destination}, "
        f"dates={departure_date} to {return_date}, "
        f"travelers={adults} adults + {children} children + {infants} infants, "
        f"interests={interests}"
    )

    # Auto-derive return_date when departure + duration are known but return is missing.
    # This handles "5-day trip to Bali, next Monday" where parse_dates returns
    # departure_date + trip_duration_days but no return_date.
    if (
        result.get("departure_date")
        and not result.get("return_date")
        and trip_duration_days
    ):
        try:
            dep = datetime.strptime(result["departure_date"], "%Y-%m-%d")
            # Inclusive counting: a 5-day trip departing May 1 returns May 5
            # (days 1,2,3,4,5), so return = departure + (duration - 1).
            ret = dep + timedelta(days=trip_duration_days - 1)
            result["return_date"] = ret.strftime("%Y-%m-%d")
            logger.info(
                "Auto-derived return_date from departure + duration: %s + %d days = %s",
                result["departure_date"],
                trip_duration_days,
                result["return_date"],
            )
        except (ValueError, TypeError):
            pass

    # Signal "proceed" when destination + departure_date + return_date are known.
    # Both dates are required so the agent cannot auto-generate with only a
    # duration (e.g. "5 day trip") when the user never specified *when*.
    # parse_dates always returns both dates when it has enough info, so this
    # only blocks the case where dates are incomplete or LLM-inferred.
    has_destination = bool(result.get("destination"))
    has_departure = bool(result.get("departure_date"))
    has_return = bool(result.get("return_date"))
    has_dates = has_departure and has_return

    if has_destination and has_dates:
        origin_iata = result.get("origin_iata")
        dest_iata = result.get("destination_iata")
        airports_note = (
            f" Airports resolved: {origin_iata} → {dest_iata}."
            if origin_iata and dest_iata
            else ""
        )
        result["status"] = "complete"
        result["message"] = f"Trip information saved.{airports_note}"
        result["instruction"] = (
            "All required trip details are saved. Proceed to generate the itinerary "
            "with generate_itinerary — do NOT ask further questions."
        )
        logger.info(
            "Trip details complete — destination + both dates present, signaling agent to proceed"
        )
    else:
        missing = []
        if not has_destination:
            missing.append("destination")
        if not has_departure:
            missing.append("departure date")
        elif not has_return:
            missing.append("return date or trip duration")
        result["status"] = "success"
        result["message"] = "Trip information saved successfully"
        result["instruction"] = (
            f"Trip info saved but still missing: {', '.join(missing)}. "
            "Continue collecting missing details before generating the itinerary."
        )

    # Return JSON string for LangChain ToolMessage serialization
    return json.dumps(result)
