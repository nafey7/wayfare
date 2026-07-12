"""Airport resolution tool for LangGraph flight agent.

This tool wraps the AirportService to resolve user location input to
airport IATA codes, handling disambiguation scenarios.

Uses either mwgg/Airports (default) or FlightLogic API based on
VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS environment variable.
"""

import logging
import re
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# IATA Multi-Airport City (MAC) codes per IATA Resolution 011c.
# Maps MAC code to the canonical city name used by mwgg/Airports.
# When the user query is a MAC code, we (a) treat it as a city query
# (query_is_city_name=True) so FlightLogic returns flights from all
# airports in the metro area, and (b) substitute the city name for
# resolution because mwgg/Airports indexes by city, not by MAC.
_IATA_MAC_TO_CITY: dict[str, str] = {
    "LON": "London",
    "NYC": "New York",
    "WAS": "Washington",
    "PAR": "Paris",
    "CHI": "Chicago",
    "DTT": "Detroit",
    "HOU": "Houston",
    "MIA": "Miami",
    "TYO": "Tokyo",
    "OSA": "Osaka",
    "SEL": "Seoul",
    "BJS": "Beijing",
    "SHA": "Shanghai",
    "JKT": "Jakarta",
    "KUL": "Kuala Lumpur",
    "TPE": "Taipei",
    "BKK": "Bangkok",
    "MIL": "Milan",
    "ROM": "Rome",
    "STO": "Stockholm",
    "MOW": "Moscow",
    "IST": "Istanbul",
    "BUE": "Buenos Aires",
    "RIO": "Rio de Janeiro",
    "SAO": "Sao Paulo",
    "YMQ": "Montreal",
    "YTO": "Toronto",
    "TCI": "Tenerife",
}
# Region modifiers that turn "<city>" into a still-the-city query.
# Used in rule 3 to tolerate "Greater London", "London Region", etc.
_REGION_PREFIXES = ("greater", "metropolitan", "metro")
_REGION_SUFFIXES = ("region", "area", "metro", "metropolitan")


def _strip_region_modifiers(s: str) -> str:
    """Remove leading/trailing region modifiers so 'Greater London' → 'London'."""
    s = s.strip().lower()
    for prefix in _REGION_PREFIXES:
        token = f"{prefix} "
        if s.startswith(token):
            s = s[len(token) :]
            break
    for suffix in _REGION_SUFFIXES:
        token = f" {suffix}"
        if s.endswith(token):
            s = s[: -len(token)]
            break
    return s.strip()


def _is_city_name(query: str, airport_city: str | None = None) -> bool:
    """Detect if query refers to a city (multi-airport) vs a specific airport.

    Detection rules (in order):
    1. Empty/invalid → True (default to city)
    2. Query is a known IATA MAC code (LON, NYC, etc.) → True
    3. Query (case-insensitive) matches the resolved airport's city → True
       3a. Same after stripping region modifiers ("Greater London" → "London") → True
    4. Pre-resolution fallback: 3-letter code → False; everything else → True

    Args:
        query: User-typed location string.
        airport_city: City field of the resolved airport. When provided
            (post-resolution), enables the precise rule 3 check. When None,
            we fall back to the naive rule 4 check.

    Examples (with airport_city):
        ("London", "London") → True (city query)
        ("Greater London", "London") → True (region modifier stripped)
        ("Gatwick", "London") → False (airport name, city ≠ query)
        ("London Gatwick", "London") → False (specific airport)
        ("LHR", "London") → False (IATA code)
        ("NYC", any) → True (MAC code, rule 2)
    """
    if not query or not isinstance(query, str):
        return True  # Default to city

    trimmed = query.strip()

    # Rule 2: IATA MAC code → always city-wise
    if trimmed.upper() in _IATA_MAC_TO_CITY:
        return True

    # Rule 3: post-resolution — query matches resolved airport's city field
    # (with tolerance for region modifiers like "Greater London" → "London").
    if airport_city is not None:
        city_norm = airport_city.strip().lower()
        query_norm = trimmed.lower()
        if query_norm == city_norm:
            return True
        return _strip_region_modifiers(query_norm) == city_norm

    # Rule 4: pre-resolution fallback — assume 3-letter codes are IATA, else city
    is_three_letters = len(trimmed) == 3
    matches_three_letter_pattern = re.match(r"^[A-Za-z]{3}$", trimmed) is not None
    return not (is_three_letters and matches_three_letter_pattern)


def _expand_mac_query(query: str) -> str:
    """Expand IATA MAC code to canonical city name for resolution.

    mwgg/Airports does not have entries for MAC codes (they aren't airports),
    so we substitute the city name before lookup. Returns the original query
    when not a MAC code.
    """
    if not query:
        return query
    upper = query.strip().upper()
    return _IATA_MAC_TO_CITY.get(upper, query)


class AirportInput(BaseModel):
    """Input schema for airport resolution."""

    query: str = Field(
        description="City name, airport code, or airport name to resolve"
    )
    role: str | None = Field(
        default=None,
        description="Whether this location is 'origin' or 'destination'. Always set this when resolving flight endpoints so the result clearly labels which field was resolved.",
    )
    exclude_iatas: list[str] | None = Field(
        default=None,
        description="IATA codes to exclude from nearby airport suggestions (e.g. the already-known origin)",
    )


@tool("resolve_airport", args_schema=AirportInput)
async def resolve_airport(
    query: str,
    role: str | None = None,
    exclude_iatas: list[str] | None = None,
) -> dict[str, Any]:
    """Resolve a location to airport IATA code(s).

    MANDATORY: You MUST call this tool for EVERY city, country, or location name
    before calling search_flights. NEVER guess or assume IATA codes yourself —
    your internal knowledge may be wrong or outdated. Only use IATA codes
    returned by this tool.

    Returns one of three statuses:
    - 'resolved': Single airport found, use the iata code
    - 'needs_disambiguation': Multiple options, ask user to choose
    - 'not_found': No matching airport, ask user for a specific city

    Examples:
    - "London" -> needs_disambiguation (multiple airports: LHR, LGW, STN...)
    - "LHR" -> resolved (London Heathrow)
    - "Heathrow" -> resolved (LHR)
    - "Birmingham" -> needs_disambiguation (UK vs USA)
    """
    from app.core.config import settings

    # Guard: reject queries that are clearly not location names.
    # Prevents false partial matches like "1adult" → "Rupsi India".
    stripped = query.strip()
    if not stripped or len(stripped) < 2:
        return {
            "status": "not_found",
            "instruction": f'"{query}" is not a valid location. Ask the user for a city or airport name.',
        }
    # Reject purely numeric or passenger-count patterns (e.g. "2", "1adult", "3adults")
    if re.fullmatch(
        r"\d+\s*(?:adults?|children|child|infants?|pax|passengers?)?",
        stripped,
        re.IGNORECASE,
    ):
        return {
            "status": "not_found",
            "instruction": f'"{query}" looks like a passenger count, not a location. Ask for the city or airport name.',
        }

    exclude_set = {c.upper() for c in (exclude_iatas or [])}

    if settings.VOYA_FEATURE_FLAG_USE_FLIGHTLOGIC_AIRPORTS:
        logger.debug(f"Using FlightLogic API for airport resolution: '{query}'")
        return await _resolve_via_flightlogic(query, exclude_set, role=role)

    logger.debug(f"Using mwgg/Airports for airport resolution: '{query}'")
    return await _resolve_via_mwgg(query, exclude_set, role=role)


async def _resolve_via_mwgg(
    query: str,
    exclude_iatas: set[str] | None = None,
    *,
    role: str | None = None,
) -> dict[str, Any]:
    """Resolve airport using mwgg/Airports database."""
    from app.domains.airport import get_airport_service

    # Expand IATA MAC codes (e.g. "NYC" → "New York") so resolution works.
    # We keep the original query for the city-name detection check below.
    original_query = query
    resolution_query = _expand_mac_query(query)

    service = get_airport_service()
    result = await service.resolve(resolution_query)

    # Build role label for instruction clarity (e.g. "ORIGIN resolved to FNC")
    role_upper = role.upper() if role else None
    role_prefix = f"{role_upper} resolved" if role_upper else "Resolved internally"

    if result.status == "resolved":
        airport = result.airport

        # City has no own airport — nearby alternatives were returned as fallback.
        if result.is_nearby_fallback and result.all_airports:
            filtered = [
                a
                for a in result.all_airports
                if not exclude_iatas or a.iata not in exclude_iatas
            ]
            # Take closest 5, but ensure the country's main international hub
            # is included. Small "International" airports (e.g. Maafaru) don't
            # count — we want the primary gateway (e.g. Malé/MLE for Maldives).
            # Heuristic: if any airport beyond the top 5 has "International"
            # in its name AND is NOT already represented by a same-name variant
            # in top 5, append it (up to 6 total).
            top = filtered[:5]
            top_iatas = {a.iata for a in top}
            for a in filtered[5:]:
                if "international" in a.name.lower() and a.iata not in top_iatas:
                    top.append(a)
                    break  # only add one extra hub
            nearby_airports = top

            # Single nearby airport → auto-resolve (issue #814).
            # No point asking user to "choose" from one option.
            if len(nearby_airports) == 1:
                only = nearby_airports[0]
                city_label = query.title().split(",")[0].strip()
                logger.info(
                    "resolve_airport: auto-resolved '%s' → %s (single nearby)",
                    query,
                    only.iata,
                )
                return {
                    "status": "resolved",
                    "role": role,
                    "iata": only.iata,
                    "name": only.name,
                    "city": only.city,
                    "country": only.country,
                    "lat": only.lat,
                    "lon": only.lon,
                    "query_is_city_name": _is_city_name(original_query, only.city),
                    "instruction": (
                        f"{role_prefix} to {only.iata} (nearest airport to {city_label}). "
                        f"This is the flight {role or 'endpoint'}. "
                        "Proceed IMMEDIATELY "
                        "(search if all fields present, else ask remaining). "
                        "Do NOT ask which airport. Do NOT re-ask for this field. "
                        f"Reference the city ('{city_label}') in reply — never airport name/IATA."
                    ),
                }

            # All nearby airports filtered out → nothing to offer
            if not nearby_airports:
                return {
                    "status": "not_found",
                    "query": query,
                    "instruction": (
                        f"No nearby airport found for '{query.title()}' "
                        "(all options already in use). Ask for a different city."
                    ),
                }

            # Multiple nearby airports → ask user to choose
            numbered = "\n".join(
                f"{i + 1}. {a.name} ({a.iata}) — {a.city}, {a.country}"
                for i, a in enumerate(nearby_airports)
            )
            logger.info(
                "resolve_airport: no_own_airport for '%s', nearby=%s",
                query,
                [a.iata for a in nearby_airports],
            )
            return {
                "status": "no_own_airport",
                "query": query,
                "nearby_airports": [
                    {
                        "iata": a.iata,
                        "name": a.name,
                        "city": a.city,
                        "country": a.country,
                    }
                    for a in nearby_airports
                ],
                "instruction": (
                    f"There's no airport directly in {query.title().split(',')[0].strip()}. "
                    f"Tell the user and ask them to choose from these nearby options:\n"
                    f"{numbered}\n"
                    "Do NOT call search_flights until the user picks one. "
                    "Do NOT mention IATA codes in your reply.\n"
                    "When the user picks an option, use the IATA code directly — "
                    "do NOT call resolve_airport again. Then call parse_dates for any "
                    "unparsed dates and search immediately if all 5 required fields are present."
                ),
            }

        return {
            "status": "resolved",
            "role": role,
            "iata": airport.iata if airport else None,
            "name": airport.name if airport else None,
            "city": airport.city if airport else None,
            "country": airport.country if airport else None,
            "lat": airport.lat if airport else None,
            "lon": airport.lon if airport else None,
            "query_is_city_name": _is_city_name(
                original_query, airport.city if airport else None
            ),  # True if "London"/"NYC"; False if "Gatwick"/"LHR"
            "instruction": (
                f"{role_prefix} to {airport.iata if airport else query}. "
                f"This is the flight {role or 'endpoint'}. "
                "Proceed IMMEDIATELY "
                "(search if all fields present, else ask remaining). Do NOT ask which airport. "
                "Do NOT re-ask for this field. "
                f"Reference the city ('{query}') in reply — never airport name/IATA."
            ),
        }

    if result.status == "needs_disambiguation":
        return {
            "status": "needs_disambiguation",
            "type": result.disambiguation_type.value
            if result.disambiguation_type
            else "unknown",
            "prompt": result.suggested_prompt,
            "options": [
                {
                    "display": opt.display_name,
                    "codes": [a.iata for a in opt.airports[:3]],
                }
                for opt in result.options
            ],
            "instruction": "Ask the user which option they meant.",
        }

    # not_found — may be a country name the LLM passed through despite the prompt rule
    return {
        "status": "not_found",
        "query": query,
        "instruction": (
            f"No airport found for '{query}'. "
            f"If this is a country name, do NOT ask 'which city?' generically. "
            f"Instead, name the 2-3 most popular international airports in that country "
            f"as a numbered list (city — airport name) and ask which the user wants to fly into. "
            f"If it is not a country, ask the user to provide a specific city or airport name."
        ),
    }


async def _resolve_via_flightlogic(
    query: str,
    exclude_iatas: set[str] | None = None,
    *,
    role: str | None = None,
) -> dict[str, Any]:
    """Resolve airport using FlightLogic API.

    FlightLogic provides a simpler resolution model - it resolves to a single
    IATA code or not found. For multi-airport cities, we check separately.
    """
    from app.domains.flight.service import FlightService

    flight_service = FlightService(current_user=None)

    # Expand IATA MAC codes (e.g. "NYC" → "New York") so FlightLogic resolution works.
    # We keep the original query for the city-name detection check below.
    original_query = query
    resolution_query = _expand_mac_query(query)

    # Try to resolve the query to an IATA code
    iata_code = await flight_service.resolve_airport(resolution_query)

    if not iata_code:
        return {
            "status": "not_found",
            "query": query,
            "instruction": f"I couldn't find any airports for '{query}'. Could you provide a specific city name? For example, if you meant a country, please tell me which city you'd like to visit.",
        }

    # Skip if this IATA was already resolved (e.g. origin same as destination)
    if exclude_iatas and iata_code in exclude_iatas:
        return {
            "status": "not_found",
            "query": query,
            "instruction": f"'{query}' resolved to {iata_code} which is already used. Ask the user for a different airport.",
        }

    # Get airport info for the resolved code
    airport_info = await flight_service.get_airport_info(iata_code)

    airport_name = (
        (airport_info.get("name") or airport_info.get("airport_name"))
        if airport_info
        else None
    )

    # FlightLogic API does not return coordinates today; this guard is a
    # forward-compatible check in case a future API version adds them.
    lat = airport_info.get("lat") if airport_info else None
    lon = airport_info.get("lon") if airport_info else None
    if lat is None or lon is None:
        # Fall back to mwgg/Airports database for coordinates
        from app.domains.airport.airport_resolver import (
            airport_resolver as mwgg_resolver,
        )

        await mwgg_resolver.ensure_loaded()
        mwgg_info = await mwgg_resolver.get_airport_info(iata_code)
        if mwgg_info:
            lat = mwgg_info.get("lat")
            lon = mwgg_info.get("lon")

    role_upper = role.upper() if role else None
    role_prefix = f"{role_upper} resolved" if role_upper else "Resolved internally"

    resolved_city = airport_info.get("city") if airport_info else None
    return {
        "status": "resolved",
        "role": role,
        "iata": iata_code,
        "name": airport_name,
        "city": resolved_city,
        "country": airport_info.get("country") if airport_info else None,
        "lat": lat,
        "lon": lon,
        "query_is_city_name": _is_city_name(
            original_query, resolved_city
        ),  # True if "London"/"NYC"; False if "Gatwick"/"LHR"
        "instruction": (
            f"{role_prefix} to {iata_code}. "
            f"This is the flight {role or 'endpoint'}. "
            "Proceed IMMEDIATELY "
            "(search if all fields present, else ask remaining). Do NOT ask which airport. "
            "Do NOT re-ask for this field. "
            f"Reference the city ('{query}') in reply — never airport name/IATA."
        ),
    }


class NearbyAirportsInput(BaseModel):
    """Input schema for nearby airport search."""

    query: str = Field(
        description="IATA code or city name to search around (e.g. 'BUF', 'Buffalo', 'London')"
    )
    radius_km: float = Field(
        default=200,
        description="Search radius in kilometres. Default 200 (roughly a 2-hour drive).",
    )


@tool("find_nearby_airports", args_schema=NearbyAirportsInput)
async def find_nearby_airports(query: str, radius_km: float = 200) -> dict[str, Any]:
    """Find airports near a city or IATA code.

    Use this tool when:
    - User asks 'any airports near X', 'any around X', 'airports close to X'
    - A search failed due to an unsupported airport and user wants regional alternatives

    Returns up to 5 nearby airports sorted by distance, plus the country's main
    international hub if it isn't already in the top 5.
    """
    from app.domains.airport.airport_resolver import AirportResolver

    resolver = AirportResolver()

    # Resolve query to IATA code first (handles both city names and IATA codes)
    resolved = await _resolve_via_mwgg(query)
    if resolved["status"] != "resolved":
        return {
            "status": "not_found",
            "instruction": f"Could not resolve '{query}' to an airport. Ask the user to clarify the location.",
        }

    iata_code = resolved["iata"]
    # Fetch extra results so we can check for an international hub beyond top 5
    nearby = await resolver.find_nearby_airports(
        iata_code, radius_km=radius_km, limit=10
    )

    if not nearby:
        return {
            "status": "no_results",
            "reference_airport": iata_code,
            "instruction": (
                f"No airports found within {radius_km:.0f} km of {iata_code}. "
                "Inform the user and suggest trying a nearby major city instead."
            ),
        }

    # Take closest 5, but ensure the country's main international hub is
    # included (e.g. Malé/MLE for Maldives). If an "International" airport
    # exists beyond position 5, append it (max 6 total).
    top = nearby[:5]
    top_iatas = {a["iata"] for a in top}
    for a in nearby[5:]:
        if "international" in a.get("name", "").lower() and a["iata"] not in top_iatas:
            top.append(a)
            break  # only add one extra hub

    return {
        "status": "success",
        "reference_airport": iata_code,
        "airports": top,
        "instruction": (
            "Present the nearest 5 airports as a numbered list with city name "
            "and distance. If an international hub was appended beyond the top 5, "
            "present it last and note it is the main international gateway. "
            "Ask the user which they would like to fly into."
        ),
    }


__all__ = [
    "AirportInput",
    "NearbyAirportsInput",
    "find_nearby_airports",
    "resolve_airport",
]
