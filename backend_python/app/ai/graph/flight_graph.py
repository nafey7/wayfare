"""LangGraph flight booking agent.

This module creates and manages the ReAct agent for flight booking conversations.
Uses MongoDB checkpointer for conversation state persistence.
"""

import json
import logging
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.ai.graph.base import create_agent_engine, create_checkpointer
from app.ai.graph.state import FlightState
from app.ai.graph.suggestion_chips import parse_suggestions
from app.ai.graph.tools import (
    find_nearby_airports,
    hand_back_to_supervisor,
    parse_dates,
    resolve_airport,
    search_flights,
)
from app.ai.graph.tracing import generate_message_id, traced_observation
from app.ai.graph.utils import (
    build_hand_back_response,
    detect_hand_back_tool,
    extract_last_ai_message,
    extract_text_content,
)

logger = logging.getLogger(__name__)

# Keyword mapping for detecting destination preferences (e.g., "warm place", "beach")
DESTINATION_PREFERENCE_KEYWORDS: dict[str, list[str]] = {
    "warm": [
        "warm",
        "hot",
        "sunny",
        "tropical",
        "heat",
        "sunshine",
        "somewhere warm",
        "warm place",
    ],
    "cold": ["cold", "cool", "chilly", "winter destination"],
    "beach": ["beach", "seaside", "coastal", "island", "ocean", "sea"],
    "ski": ["ski", "skiing", "snow", "snowboard", "slopes", "alpine"],
    "mountain": ["mountain", "hiking", "trekking"],
    "city": ["city break", "urban", "metropolitan"],
}


def _detect_destination_preference(message: str) -> str | None:
    """Detect destination preference keywords in user message.

    Checks for broad travel preference keywords like "warm", "beach", "ski"
    that indicate the user wants a TYPE of destination rather than a specific city.

    Args:
        message: User's message text

    Returns:
        Preference category string (e.g., "warm", "beach") or None
    """
    message_lower = message.lower()
    for preference, keywords in DESTINATION_PREFERENCE_KEYWORDS.items():
        for kw in keywords:
            if " " in kw:
                # Multi-word phrases: substring match is already specific enough
                if kw in message_lower:
                    return preference
            elif re.search(r"\b" + re.escape(kw) + r"\b", message_lower):
                # Single words: word boundary prevents "hot" matching "hotel",
                # "sea" matching "season"/"search"/"seat", "island" matching "Iceland"
                return preference
    return None


# Module-level singletons for efficiency
_checkpointer: MongoDBSaver | None = None
_mongo_client: MongoClient[dict[str, Any]] | None = None
_compiled_graph: Any = None
_flight_inner_agent: Any = None


def _get_formatted_prompt() -> str:
    """Get the system prompt from Langfuse with fallback to hardcoded."""
    from app.ai.prompt_management import get_flight_prompt

    return get_flight_prompt()


_FLIGHT_TOOLS = [
    resolve_airport,
    parse_dates,
    search_flights,
    find_nearby_airports,
    hand_back_to_supervisor,
]


def _create_flight_engine(
    checkpointer: MongoDBSaver | None = None,
    state_schema: type | None = None,
) -> Any:
    """Create flight agent engine with static prompt (V1 standalone path)."""
    return create_agent_engine(
        tools=_FLIGHT_TOOLS,
        component="agent_flight",
        prompt_fn=_get_formatted_prompt,
        checkpointer=checkpointer,
        state_schema=state_schema,
    )


def get_flight_inner_agent() -> Any:
    """Get stateless flight agent engine for V2 supervisor (dynamic prompt).

    Uses ``dynamic_prompt_enabled=True`` so the system prompt is fetched fresh
    from Langfuse on every invocation via ``PromptContext``, rather than being
    baked in at singleton creation time.
    """
    global _flight_inner_agent
    if _flight_inner_agent is None:
        logger.info("Creating stateless flight inner agent for V2 supervisor")
        _flight_inner_agent = create_agent_engine(
            tools=_FLIGHT_TOOLS,
            component="agent_flight",
            dynamic_prompt_enabled=True,
        )
    return _flight_inner_agent


def get_flight_graph() -> Any:
    """Get compiled flight graph with MongoDB checkpointer (singleton).

    V1 path — standalone graph with its own checkpointer and FlightState schema.
    """
    global _compiled_graph, _checkpointer, _mongo_client

    if _compiled_graph is None:
        logger.info("Creating flight graph with MongoDB checkpointer")
        _checkpointer, _mongo_client = create_checkpointer("flight")
        _compiled_graph = _create_flight_engine(
            checkpointer=_checkpointer, state_schema=FlightState
        )

    return _compiled_graph


def _extract_collected_flight_params(messages: list[Any]) -> dict[str, Any]:
    """Extract collected flight parameters from tool messages.

    Scans resolve_airport and search_flights tool results to build
    a dict of collected flight params for shared_context.

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with collected flight params (origin, destination, dates, adults,
        origin_city, destination_city — city names preferred over IATA codes)
    """
    params: dict[str, Any] = {}

    # Extract city names from resolve_airport responses first
    city_map, _ = _extract_airport_resolution_data(messages)

    # Enrich city_map from search_flights results — the backend always resolves
    # IATA → city name in search_params, so this covers cases where resolve_airport
    # was never called (e.g. user picked from a country suggestion list and LLM
    # used the IATA code directly in search_flights).
    _enrich_city_map_from_search_results(messages, city_map)

    # Track resolve_airport calls to know origin vs destination order
    resolved_airports: list[dict[str, Any]] = []

    for msg in messages:
        # Extract from resolve_airport tool results (available before search)
        if isinstance(msg, ToolMessage) and msg.name == "resolve_airport":
            try:
                content = msg.content
                result = json.loads(content) if isinstance(content, str) else content
                if (
                    isinstance(result, dict)
                    and result.get("status") == "resolved"
                    and result.get("iata")
                ):
                    resolved_airports.append(result)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Extract from parse_dates tool results (available before search)
        if isinstance(msg, ToolMessage) and msg.name == "parse_dates":
            try:
                content = msg.content
                result = json.loads(content) if isinstance(content, str) else content
                if not isinstance(result, dict):
                    continue
                if result.get("departure_date"):
                    params["departure_date"] = result["departure_date"]
                if result.get("return_date"):
                    params["return_date"] = result["return_date"]
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls or []:
                # Extract passenger count from resolve_airport/search_flights calls
                if tool_call.get("name") == "search_flights":
                    args = tool_call.get("args", {})
                    origin_iata = args.get("origin")
                    destination_iata = args.get("destination")
                    if origin_iata:
                        params["origin"] = origin_iata
                        city_name = city_map.get(origin_iata)
                        if city_name:
                            params["origin_city"] = city_name
                    if destination_iata:
                        params["destination"] = destination_iata
                        city_name = city_map.get(destination_iata)
                        if city_name:
                            params["destination_city"] = city_name
                    if args.get("departure_date"):
                        params["departure_date"] = args["departure_date"]
                    if args.get("return_date"):
                        params["return_date"] = args["return_date"]
                    if args.get("adults"):
                        params["adults"] = args["adults"]
                    if args.get("children"):
                        params["children"] = args["children"]

    # If search_flights wasn't called yet, use resolve_airport results.
    # Only assign origin/destination when 2+ airports were resolved in the same turn
    # (first=origin, second=destination by convention — e.g. "fly from London to Paris").
    # When only 1 airport is resolved and search hasn't been called, we cannot reliably
    # determine if it is origin or destination — e.g. "book flights to London" resolves
    # London but it is the destination, not origin. Assigning it as origin here would
    # corrupt shared_context and cause the classic "Paris→Paris" or "London→Paris" bug.
    if not params.get("origin") and len(resolved_airports) >= 2:
        params["origin"] = resolved_airports[0]["iata"]
        city = city_map.get(resolved_airports[0]["iata"])
        if city:
            params["origin_city"] = city
    if not params.get("destination") and len(resolved_airports) >= 2:
        params["destination"] = resolved_airports[1]["iata"]
        city = city_map.get(resolved_airports[1]["iata"])
        if city:
            params["destination_city"] = city

    return params


def process_flight_messages(
    all_messages: list[Any],
    msg_count_before: int = 0,
    message_id: str = "",
) -> dict[str, Any]:
    """Process flight agent messages into a response dict.

    Shared between V1 invoke_flight_graph and V2 supervisor dispatch.
    Handles hand_back detection, flight search results extraction, and
    airport disambiguation suggestions.
    """
    hand_back = detect_hand_back_tool(all_messages)
    if hand_back:
        resp = build_hand_back_response(all_messages, hand_back, message_id)
        # Preserve collected params so shared_context captures flight data
        # even during hand_back (needed for detour return).
        collected = _extract_collected_flight_params(all_messages)
        if collected:
            resp["collected_params"] = collected
        return resp

    response_message = extract_last_ai_message(all_messages)

    # Check for flight search results (only new messages to avoid stale results)
    new_messages = (
        all_messages[msg_count_before:] if msg_count_before > 0 else all_messages
    )

    # Check multicity first (distinct status="multicity_results" indicator)
    multicity_results = _extract_multicity_flight_search_results(new_messages)
    if multicity_results:
        logger.info(
            "Multicity flight search completed - returning %d legs",
            len(multicity_results["data"].get("multicity_legs", [])),
        )
        collected = _extract_collected_flight_params(all_messages)
        cleaned_msg, mc_suggestions = parse_suggestions(response_message or "")
        if not mc_suggestions:
            mc_suggestions = [
                {
                    "title": "Find hotels for this trip",
                    "command": "Find hotels for this trip",
                },
                {"title": "Plan a trip itinerary", "command": "Plan a trip itinerary"},
                {
                    "title": "Show me different dates",
                    "command": "Show me different dates",
                },
            ]
        return {
            "message": cleaned_msg or response_message,
            "type": "multicity_flight_search_results",
            "signal": "done",
            "data": multicity_results["data"],
            "collected_params": collected,
            "suggestions": mc_suggestions,
            "message_id": message_id,
        }

    flight_results = _extract_flight_search_results(new_messages)

    if flight_results:
        logger.info(
            "Flight search completed - returning %d flights",
            len(flight_results.get("flights", [])),
        )
        collected = _extract_collected_flight_params(all_messages)
        # Parse LLM suggestions; fall back to defaults for search results
        cleaned_msg, flight_suggestions = parse_suggestions(response_message or "")
        if not flight_suggestions:
            dest = (collected or {}).get("destination", "your destination")
            flight_suggestions = [
                {
                    "title": f"Find hotels in {dest}",
                    "command": f"Find hotels in {dest}",
                },
                {
                    "title": f"Plan a {dest} itinerary",
                    "command": f"Plan a {dest} itinerary",
                },
                {
                    "title": "Show me different dates",
                    "command": "Show me different dates",
                },
            ]
        return {
            "message": cleaned_msg or response_message,
            "type": "flight_search_results",
            "signal": "done",
            "data": flight_results["data"],
            "flights": flight_results["flights"],
            "session_id": flight_results.get("session_id", ""),
            "origin_location": flight_results.get("origin_location"),
            "destination_location": flight_results.get("destination_location"),
            "collected_params": collected,
            "suggestions": flight_suggestions,
            "message_id": message_id,
        }

    # Check for date-range flight search results
    date_range_results = _extract_flight_date_range_results(new_messages)
    if date_range_results:
        logger.info(
            "Date-range flight search completed — %d dates searched",
            len(date_range_results.get("dates", [])),
        )
        collected = _extract_collected_flight_params(all_messages)
        return {
            "message": response_message,
            "type": "flight_date_range_results",
            "signal": "done",
            "data": date_range_results,
            "collected_params": collected,
            "message_id": message_id,
        }

    # Check for airport disambiguation suggestions
    airport_suggestions = _extract_airport_suggestions(new_messages)

    # Extract collected flight params for shared_context capture
    collected = _extract_collected_flight_params(all_messages)

    return {
        "message": response_message,
        "type": "flight_conversation",
        "suggestions": airport_suggestions,
        "collected_params": collected,
        "message_id": message_id,
    }


def _extract_airport_resolution_data(
    messages: list[Any],
) -> tuple[dict[str, str], dict[str, tuple[float | None, float | None]]]:
    """Extract city names and coordinates from resolve_airport tool responses.

    Single pass over messages to build both mappings:
    - city_map: IATA -> city name (only for city-name queries, e.g. "London" -> "LHR": "London")
    - coord_map: IATA -> (lat, lon) coordinates from the airport database

    Args:
        messages: List of LangGraph messages

    Returns:
        Tuple of (city_map, coord_map)
    """
    city_map: dict[str, str] = {}
    coord_map: dict[str, tuple[float | None, float | None]] = {}

    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name == "resolve_airport":
            try:
                content = msg.content
                result = json.loads(content) if isinstance(content, str) else content

                if not isinstance(result, dict):
                    continue

                status = result.get("status")

                if status == "resolved":
                    iata = result.get("iata")
                    if not iata:
                        continue

                    # City name mapping (only for city-name queries)
                    city = result.get("city")
                    query_is_city = result.get("query_is_city_name", False)
                    if city and query_is_city:
                        city_map[iata] = city
                        logger.debug("Mapped %s -> %s (city search)", iata, city)

                    # Coordinates mapping (always, for map markers)
                    coord_map[iata] = (result.get("lat"), result.get("lon"))

                elif status == "no_own_airport":
                    # City has no own airport — user was shown nearby alternatives.
                    # Pre-populate city_map from the nearby list so that when the
                    # user picks one and search_flights is called, city_map.get(iata)
                    # returns the city name (e.g. MBO → "Mamburao") and
                    # destination_city is captured into shared_context correctly.
                    for nearby in result.get("nearby_airports", []):
                        nearby_iata = nearby.get("iata")
                        nearby_city = nearby.get("city")
                        if nearby_iata and nearby_city:
                            city_map[nearby_iata] = nearby_city
                            logger.debug(
                                "Mapped nearby %s -> %s (no_own_airport fallback)",
                                nearby_iata,
                                nearby_city,
                            )

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning("Failed to parse resolve_airport result: %s", e)
                continue

    return city_map, coord_map


def _enrich_city_map_from_search_results(
    messages: list[Any],
    city_map: dict[str, str],
) -> None:
    """Enrich city_map with city names from search_flights tool results.

    When the LLM uses an IATA code directly in search_flights without calling
    resolve_airport first (e.g. user picked from a country suggestion list),
    city_map won't have the city name. The search_flights backend result always
    includes ``search_params`` with resolved city names — extract them as
    fallback so downstream consumers (shared_context → hotel agent) get city
    names instead of bare IATA codes.

    Pairs each search_flights tool **call** (AIMessage with IATA args) with its
    **result** (ToolMessage with city-name search_params) via tool_call_id.

    Mutates ``city_map`` in place (only adds missing entries, never overwrites).
    """
    # 1. Index search_flights tool calls: call_id → {origin, destination} IATA codes
    call_iatas: dict[str, dict[str, str]] = {}
    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls or []:
                if tc.get("name") == "search_flights":
                    call_id = tc.get("id") or tc.get("call_id") or ""
                    if call_id:
                        args = tc.get("args", {})
                        call_iatas[call_id] = {
                            "origin": args.get("origin", ""),
                            "destination": args.get("destination", ""),
                        }

    # 2. Match ToolMessage results to their tool calls
    for msg in messages:
        if not (isinstance(msg, ToolMessage) and msg.name == "search_flights"):
            continue
        try:
            # Issue #1034: search_params lives on `msg.artifact` for the new
            # content+artifact split. Fall back to content for legacy/test
            # messages that still carry `search_params` inline.
            artifact = getattr(msg, "artifact", None)
            sp: dict[str, Any] | None = None
            if isinstance(artifact, dict):
                sp = artifact.get("search_params") or None
            if not sp:
                content = msg.content
                result = json.loads(content) if isinstance(content, str) else content
                if not isinstance(result, dict) or result.get("status") != "success":
                    continue
                sp = result.get("search_params", {})
            if not sp:
                continue

            # Get IATA codes from the matching tool call
            call_id = getattr(msg, "tool_call_id", "")
            iatas = call_iatas.get(call_id, {})
            origin_iata = iatas.get("origin", "")
            dest_iata = iatas.get("destination", "")

            # search_params.origin/destination are city names from the backend
            origin_city = sp.get("origin", "")
            dest_city = sp.get("destination", "")

            if origin_iata and origin_city and origin_iata not in city_map:
                city_map[origin_iata] = origin_city
                logger.debug(
                    "Mapped %s -> %s (from search_flights result)",
                    origin_iata,
                    origin_city,
                )
            if dest_iata and dest_city and dest_iata not in city_map:
                city_map[dest_iata] = dest_city
                logger.debug(
                    "Mapped %s -> %s (from search_flights result)",
                    dest_iata,
                    dest_city,
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            continue


def _build_location(lat: float | None, lon: float | None) -> dict[str, float] | None:
    """Convert lat/lon to ``{"latitude": ..., "longitude": ...}`` or ``None``."""
    if lat is not None and lon is not None:
        return {"latitude": lat, "longitude": lon}
    return None


def _extract_search_params_from_messages(messages: list[Any]) -> dict[str, Any]:
    """Extract search parameters from the tool call that triggered the search.

    Scans messages for the AIMessage containing the search_flights tool call
    to extract the original search parameters.

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with search parameters (origin, destination, dates, passengers)
        Includes origin_city/destination_city if the search was by city name
    """
    # Extract city names and coordinates from resolve_airport responses (single pass)
    city_map, coord_map = _extract_airport_resolution_data(messages)
    # Enrich from search_flights results (covers IATA-only calls without resolve_airport)
    _enrich_city_map_from_search_results(messages, city_map)

    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls or []:
                if tool_call.get("name") == "search_flights":
                    args = tool_call.get("args", {})
                    origin_iata = args.get("origin", "")
                    destination_iata = args.get("destination", "")

                    # Extract city search flags
                    origin_is_city = args.get("origin_is_city", True)
                    destination_is_city = args.get("destination_is_city", True)

                    # Get city names from resolve_airport responses (if available)
                    origin_city_name = city_map.get(origin_iata)
                    destination_city_name = city_map.get(destination_iata)

                    params = {
                        # CRITICAL: Use city name for URL when origin_is_city=True
                        # "London" (city search) vs "LHR" (airport search)
                        # This ensures the redirect URL shows the original search intent
                        "origin": origin_city_name
                        if (origin_is_city and origin_city_name)
                        else origin_iata,
                        "destination": destination_city_name
                        if (destination_is_city and destination_city_name)
                        else destination_iata,
                        "departure_date": args.get("departure_date", ""),
                        "return_date": args.get("return_date"),
                        "journey_type": "RoundTrip"
                        if args.get("return_date")
                        else "OneWay",
                        "passengers": {
                            "adults": args.get("adults", 1),
                            "children": args.get("children", 0),
                            "infants": args.get("infants", 0),
                        },
                        "origin_is_city": origin_is_city,
                        "destination_is_city": destination_is_city,
                        "cabin_class": {
                            "economy": "Economy",
                            "premium_economy": "PremiumEconomy",
                            "business": "Business",
                            "first": "First",
                        }.get(
                            (args.get("cabin_class") or "economy").lower(), "Economy"
                        ),
                        "direct_flight": 1 if args.get("max_stops") == 0 else 0,
                        "max_stops": args.get("max_stops"),
                        "price_min": args.get("price_min"),
                        "price_max": args.get("price_max"),
                        "preferred_airline": args.get("preferred_airline"),
                        "max_outbound_duration": args.get("max_outbound_duration"),
                        "max_inbound_duration": args.get("max_inbound_duration"),
                    }

                    # Add city names and IATA codes as separate fields
                    if origin_city_name:
                        params["origin_city"] = origin_city_name
                    if destination_city_name:
                        params["destination_city"] = destination_city_name
                    # Include original IATA codes so frontend can use them
                    # directly instead of re-resolving city names
                    params["origin_iata"] = origin_iata
                    params["destination_iata"] = destination_iata

                    # Add location coordinates from resolve_airport results
                    origin_coords = coord_map.get(origin_iata, (None, None))
                    dest_coords = coord_map.get(destination_iata, (None, None))
                    params["origin_location"] = _build_location(*origin_coords)
                    params["destination_location"] = _build_location(*dest_coords)

                    return params
    return {}


def _extract_flight_search_results(messages: list[Any]) -> dict[str, Any] | None:
    """Extract flight search results from tool messages.

    Scans messages for search_flights tool output and transforms it
    into the frontend-expected format.

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with frontend-compatible flight data, or None if no results found
    """
    # First, extract search params from the tool call
    search_params = _extract_search_params_from_messages(messages)

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "search_flights":
            try:
                # Issue #1034: full payload now lives on `msg.artifact`
                # (response_format="content_and_artifact"). The LLM only saw
                # the summary in msg.content. We read the artifact for the
                # frontend payload.
                artifact = getattr(msg, "artifact", None)
                if not artifact:
                    # Successful searches now ALWAYS carry an artifact. If
                    # missing, this is either a non-success status or a stale
                    # message format — skip.
                    continue
                if not isinstance(artifact, dict):
                    continue
                # Success artifacts (from _split_search_result) carry no
                # ``status`` key — only multicity / date-range artifacts do.
                # Skip those so the dedicated extractors at
                # ``_extract_multicity_flight_search_results`` and
                # ``_extract_flight_date_range_results`` get to claim them.
                # Without this guard a date-range artifact (which carries
                # ``dates`` but not ``flights``) would be mis-claimed here
                # and surface as "0 flights" instead of the per-date
                # breakdown.
                if artifact.get("status") in (
                    "multicity_results",
                    "date_range_results",
                ):
                    continue

                summary = artifact.get("summary", {})
                flights = artifact.get("flights", []) or []

                # Ensure each flight has the validating_airline structure the
                # frontend expects, without re-deduping (list is already unique).
                for flight in flights:
                    if "validating_airline" not in flight:
                        flight["validating_airline"] = {
                            "airline_name": flight.get("airline", "Unknown"),
                            "iata_code": flight.get("airline_code", ""),
                        }

                # Extract FlightLogic session_id from artifact (required for revalidation)
                flightlogic_session_id = artifact.get("session_id")
                if not flightlogic_session_id:
                    logger.warning(
                        "Flight search artifact missing session_id - revalidation may fail"
                    )

                # Prefer enriched city names (e.g. "London") from artifact
                # over IATA codes from message params.
                tool_sp = artifact.get("search_params", {})
                if tool_sp.get("origin"):
                    search_params["origin"] = tool_sp["origin"]
                if tool_sp.get("destination"):
                    search_params["destination"] = tool_sp["destination"]
                logger.info("🔍 search_params for frontend: %s", search_params)
                logger.info(
                    "📦 [extract] flight artifact → %d flights ready for frontend "
                    "(summary.total_found=%s, has_session=%s)",
                    len(flights),
                    summary.get("total_found"),
                    bool(flightlogic_session_id),
                )

                return {
                    "data": {
                        "search_params": search_params,
                        "origin_is_city": artifact.get("origin_is_city", True),
                        "destination_is_city": artifact.get(
                            "destination_is_city", True
                        ),
                        "summary": {
                            "total_flights": summary.get("total_found", 0),
                            "direct_count": summary.get("direct_flights", 0),
                            "price_range": summary.get("price_range", {}),
                        },
                    },
                    "flights": flights,
                    "session_id": flightlogic_session_id or "",
                    "origin_location": search_params.get("origin_location"),
                    "destination_location": search_params.get("destination_location"),
                }

            except (KeyError, TypeError) as e:
                logger.warning("Failed to parse flight search artifact: %s", e)
                continue

    return None


def _extract_multicity_flight_search_results(
    messages: list[Any],
) -> dict[str, Any] | None:
    """Extract multi-city flight search results from tool messages.

    Scans for a ``search_flights`` ToolMessage with ``status="multicity_results"``
    and transforms it into the ``multicity_flight_search_results`` frontend format
    (§8.2 payload shape).

    Args:
        messages: List of LangGraph messages from the current turn.

    Returns:
        Dict with ``data`` containing ``search_params``, ``multicity_parallel``,
        and ``multicity_legs``; or ``None`` if no multicity result found.
    """
    _, coord_map = _extract_airport_resolution_data(messages)

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "search_flights":
            try:
                # Issue #1034: full multicity payload (with flights per leg)
                # is on msg.artifact. The content has the leg metadata only.
                artifact = getattr(msg, "artifact", None)
                if not isinstance(artifact, dict):
                    continue
                if artifact.get("status") != "multicity_results":
                    continue

                raw_legs: list[dict[str, Any]] = artifact.get("multicity_legs", [])
                search_params: dict[str, Any] = artifact.get("search_params", {})

                # Enrich each leg with map coordinates from resolve_airport results
                enriched_legs: list[dict[str, Any]] = []
                for leg in raw_legs:
                    origin_iata = str(leg.get("origin", ""))
                    dest_iata = str(leg.get("destination", ""))
                    origin_coords = coord_map.get(origin_iata, (None, None))
                    dest_coords = coord_map.get(dest_iata, (None, None))

                    enriched_leg = dict(leg)
                    enriched_leg["origin_location"] = _build_location(*origin_coords)
                    enriched_leg["destination_location"] = _build_location(*dest_coords)
                    enriched_legs.append(enriched_leg)

                logger.info("Multicity search extracted: %d legs", len(enriched_legs))
                return {
                    "data": {
                        "search_params": search_params,
                        "multicity_parallel": True,
                        "multicity_legs": enriched_legs,
                    }
                }

            except (KeyError, TypeError) as e:
                logger.warning(
                    "Failed to parse multicity flight search artifact: %s", e
                )
                continue

    return None


def _extract_flight_date_range_results(
    messages: list[Any],
) -> dict[str, Any] | None:
    """Extract date-range flight search results from tool messages.

    Scans for search_flights tool output with status ``date_range_results``
    and returns the aggregated per-date data for the frontend.
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "search_flights":
            try:
                # Issue #1034: per-date flights are on msg.artifact, not content.
                artifact = getattr(msg, "artifact", None)
                if not isinstance(artifact, dict):
                    continue
                if artifact.get("status") != "date_range_results":
                    continue

                return {
                    "dates": artifact.get("dates", []),
                    "overall_best": artifact.get("overall_best"),
                    "searched_from": artifact.get("searched_from", ""),
                    "searched_to": artifact.get("searched_to", ""),
                    "has_more": artifact.get("has_more", False),
                    "next_chunk_start": artifact.get("next_chunk_start"),
                    "next_chunk_end": artifact.get("next_chunk_end"),
                }

            except (KeyError, TypeError) as e:
                logger.warning("Failed to parse date-range flight artifact: %s", e)
                continue

    return None


def _extract_airport_suggestions(messages: list[Any]) -> list[dict[str, str]] | None:
    """Extract airport suggestions from resolve_airport tool messages.

    When the resolve_airport tool returns "needs_user_choice" status,
    this extracts the airport options as clickable suggestions for the frontend.

    Args:
        messages: List of LangGraph messages

    Returns:
        List of suggestion dicts with title/command, or None if no disambiguation needed
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "resolve_airport":
            try:
                content = msg.content
                if isinstance(content, str):
                    tool_result = json.loads(content)
                else:
                    tool_result = content

                # Check if this is a disambiguation response
                if tool_result.get("status") != "needs_user_choice":
                    continue

                airports = tool_result.get("airports", [])
                if not airports:
                    continue

                # Transform to frontend suggestion format
                return [
                    {
                        "title": f"{airport['name']} ({airport['iata']})",
                        "command": airport["iata"],
                    }
                    for airport in airports
                ]

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning("Failed to parse airport suggestions: %s", e)
                continue

    return None


async def invoke_flight_graph(
    message: str,
    user_id: str,
    chat_id: str,
    flight_params: dict[str, Any] | None = None,
    user_email: str | None = None,
    context_hint: str | None = None,
) -> dict[str, Any]:
    """Invoke the flight graph for a user message.

    This is the main entry point for the ChatService integration.
    The graph automatically loads previous state from MongoDB using
    chat_id as thread_id.

    Args:
        message: User's message text
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (used as thread_id for checkpointing)
        flight_params: Optional existing flight parameters to merge
        user_email: Optional user email for Langfuse tracing

    Returns:
        Dict containing:
        - message: AI response text
        - type: Response type for frontend rendering
        - data: Optional additional data (flight cards, etc.)
        - flight: Updated flight parameters
        - message_id: Message ID for feedback correlation
    """
    graph = get_flight_graph()

    # Generate message_id for feedback correlation
    message_id = generate_message_id()

    # Check if flight_params are complete (from supervisor/itinerary)
    # Params are ONLY complete if we have ALL required fields for search:
    # - origin, destination, departure_date (essential travel info)
    # - return_date (must be explicitly set for round-trip, or None after user confirms one-way)
    # - adults (must be set, can't default to 1 without asking user)
    flight_params_dict = flight_params or {}

    # DEBUG: Log what we received
    logger.info("Flight params received: %s", flight_params_dict)

    # Handle origin_raw/destination_raw (from chat service extraction)
    # With multi-airport search, we no longer need to override the message
    # Agent will extract everything (origin, destination, dates) from the original message
    if flight_params_dict.get("origin_raw") or flight_params_dict.get(
        "destination_raw"
    ):
        origin_raw = flight_params_dict.get("origin_raw")
        destination_raw = flight_params_dict.get("destination_raw")

        logger.info(
            f"🔍 Chat service extracted: origin_raw={origin_raw}, destination_raw={destination_raw}"
        )
        logger.info(
            f"🔍 Preserving original message for agent to extract dates: '{message[:100]}...'"
        )

        # Remove origin_raw/destination_raw so agent doesn't see them
        # Agent will extract origin, destination, AND dates from the original message
        flight_params_dict = {
            k: v
            for k, v in flight_params_dict.items()
            if k not in ["origin_raw", "destination_raw"]
        }

    # Detect destination preference if no specific destination provided
    if not flight_params_dict.get("destination"):
        preference = _detect_destination_preference(message)
        if preference:
            flight_params_dict["destination_preference"] = preference
            logger.info("Detected destination preference: %s", preference)

    has_origin = bool(flight_params_dict.get("origin"))
    has_destination = bool(flight_params_dict.get("destination"))
    has_departure_date = bool(flight_params_dict.get("departure_date"))
    has_trip_type = (
        "return_date" in flight_params_dict
    )  # Must be explicitly set (even if None for one-way)
    adults_count = flight_params_dict.get("adults")
    has_passengers = adults_count is not None and adults_count > 0

    # DEBUG: Log what we detected
    logger.info(
        f"🔍 Param check: has_origin={has_origin}, has_destination={has_destination}, "
        f"has_departure_date={has_departure_date}, has_trip_type={has_trip_type}, has_passengers={has_passengers}"
    )

    # Only consider complete if we have ALL required info (including trip type and passengers)
    params_complete = (
        has_origin
        and has_destination
        and has_departure_date
        and has_trip_type
        and has_passengers
    )
    logger.info("Params complete: %s", params_complete)

    # Config with thread_id enables automatic state loading/saving.
    # user_id is included so InjectedToolArg tools (e.g. search_flights) can
    # fetch the user's saved preferences without it being an LLM parameter.
    config: dict[str, Any] = {
        "configurable": {"thread_id": chat_id, "user_id": user_id}
    }

    # Get current checkpoint state BEFORE invoking
    # This serves two purposes:
    # 1. Check if conversation already exists (for itinerary param handling)
    # 2. Count messages to only check NEW messages for flight results (stale results fix)
    msg_count_before = 0
    existing_state = None
    try:
        current_state = graph.get_state(config)
        if current_state and current_state.values:
            existing_state = current_state
            existing_messages = current_state.values.get("messages", [])
            msg_count_before = len(existing_messages)
            logger.debug(
                "Checkpoint has %d existing messages for chat_id=%s",
                msg_count_before,
                chat_id,
            )
            logger.info("🔍 Existing state found: True")
        else:
            logger.info("🔍 Existing state found: False (empty)")
    except Exception as e:
        # If we can't get state, assume no prior messages (new chat)
        logger.debug("Could not get checkpoint state: %s", e)
        logger.info("🔍 Existing state found: False (exception)")

    # Override message based on param completeness (for itinerary/supervisor integration)
    if params_complete and not existing_state:
        # ALL params complete - search immediately
        trip_type = "round-trip" if flight_params_dict.get("return_date") else "one-way"
        return_info = (
            f" returning {flight_params_dict.get('return_date')}"
            if flight_params_dict.get("return_date")
            else ""
        )

        logger.info(
            f"Flight params FULLY pre-populated (FIRST call): {flight_params_dict.get('origin')} → "
            f"{flight_params_dict.get('destination')}, {flight_params_dict.get('departure_date')}{return_info} "
            f"({trip_type}, {flight_params_dict.get('adults', 1)} adults) - will search immediately"
        )
        # Override user message to trigger immediate search
        # CRITICAL: Include origin_is_city and destination_is_city flags so LLM uses them
        origin_is_city = flight_params_dict.get("origin_is_city", True)
        destination_is_city = flight_params_dict.get("destination_is_city", True)
        message = (
            f"Search flights from {flight_params_dict.get('origin')} to {flight_params_dict.get('destination')} "
            f"departing {flight_params_dict.get('departure_date')}{return_info} "
            f"for {flight_params_dict.get('adults', 1)} adults. "
            f"CRITICAL: flight.origin_is_city={origin_is_city}, flight.destination_is_city={destination_is_city}. "
            f"Use these EXACT values when calling search_flights. Don't ask me any questions."
        )
    elif (
        not params_complete
        and not existing_state
        and (has_origin or has_destination or has_departure_date)
    ):
        # PARTIAL params - give context about what's filled
        logger.info(
            f"🎯 Taking PARTIAL params path: origin={flight_params_dict.get('origin')}, "
            f"destination={flight_params_dict.get('destination')}, departure={flight_params_dict.get('departure_date')} "
            f"- will ask for missing fields"
        )
        # Build message listing what's already filled
        filled_parts = []
        if has_origin:
            origin_display = flight_params_dict.get(
                "origin_name", flight_params_dict.get("origin")
            )
            filled_parts.append(f"origin: {origin_display}")
        if has_destination:
            dest_display = flight_params_dict.get(
                "destination_name", flight_params_dict.get("destination")
            )
            filled_parts.append(f"destination: {dest_display}")
        if has_departure_date:
            filled_parts.append(
                f"departure: {flight_params_dict.get('departure_date')}"
            )

        # CRITICAL: Include origin_is_city and destination_is_city flags
        origin_is_city = flight_params_dict.get("origin_is_city", True)
        destination_is_city = flight_params_dict.get("destination_is_city", True)

        # Build list of what's missing
        missing_parts = []
        if not has_trip_type:
            missing_parts.append("trip type (one-way/round-trip)")
        if not has_passengers:
            missing_parts.append("number of passengers")

        missing_str = " and ".join(missing_parts) if missing_parts else "nothing"

        message = (
            f"I want to book flights. CRITICAL: Use these EXACT values from flight state:\n"
            f"- flight.origin = {flight_params_dict.get('origin')} (DO NOT resolve again)\n"
            f"- flight.destination = {flight_params_dict.get('destination')} (DO NOT resolve again)\n"
            f"- flight.departure_date = {flight_params_dict.get('departure_date')}\n"
        )

        # Only include return_date if it exists and is not None
        if has_trip_type and flight_params_dict.get("return_date"):
            message += f"- flight.return_date = {flight_params_dict.get('return_date')} (round-trip)\n"

        message += (
            f"- flight.origin_is_city = {origin_is_city}\n"
            f"- flight.destination_is_city = {destination_is_city}\n"
            f"These values are FINAL - use them directly in search_flights.\n"
            f"Ask me ONLY for: {missing_str}."
        )
    elif params_complete and existing_state:
        # Conversation in progress - preserve user message
        logger.info(
            f"Flight params complete but conversation exists - preserving user message: '{message[:50]}...'"
        )

    # Initial state - will be merged with checkpoint history
    # context_hint (from supervisor on agent switch) is a SystemMessage so user
    # content cannot escape into the context bracket (prompt injection prevention).
    messages: list[Any] = []
    if context_hint:
        messages.append(SystemMessage(content=context_hint))
    messages.append(HumanMessage(content=message))
    input_state: dict[str, Any] = {
        "messages": messages,
        "user_id": user_id,
        "chat_id": chat_id,
        "flight": flight_params_dict,
    }

    logger.info("Final message being sent to agent: %s...", message[:200])
    logger.debug(
        "Invoking flight graph for chat_id=%s, message=%s...",
        chat_id,
        message[:50],
    )

    # Use traced_observation for Langfuse tracing with our message_id
    with traced_observation(
        message_id=message_id,
        session_id=chat_id,
        user_id=user_id,
        user_email=user_email,
        name="flight-agent",
    ) as (_, callbacks, trace_metadata):
        # Add tracing callbacks/metadata to existing config
        if callbacks:
            config["callbacks"] = callbacks
        if trace_metadata:
            config["metadata"] = trace_metadata

        # Invoke graph asynchronously
        # Handle race condition: if state has incomplete tool calls, clear and retry
        try:
            result = await graph.ainvoke(input_state, config)
        except ValueError as e:
            error_msg = str(e)
            if "tool_calls" in error_msg and "ToolMessage" in error_msg:
                # Race condition detected: incomplete tool calls in checkpoint
                logger.warning(
                    f"Detected incomplete tool calls in checkpoint for chat_id={chat_id}. "
                    "Clearing state and retrying..."
                )

                # Race condition detected - state has incomplete tool calls
                # The lock should prevent this, but if it happens, return a graceful error
                # Note: We can't easily clear the checkpoint without direct access to checkpointer methods
                # The lock mechanism should prevent this scenario, so this is a safety net
                logger.error(
                    f"Race condition detected for chat_id={chat_id} despite lock. "
                    "This should not happen - check lock implementation."
                )
                # Return a user-friendly error message
                return {
                    "message": "I encountered an issue processing your previous request. "
                    "Please try sending your message again.",
                    "type": "error",
                    "error": "incomplete_tool_calls",
                    "message_id": message_id,
                }
            # Re-raise if it's a different ValueError
            raise

    # Extract last AI message
    last_ai_message = None
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage):
            last_ai_message = msg
            break

    response_message = ""
    if last_ai_message:
        response_message = extract_text_content(last_ai_message.content)

    logger.debug(
        "Flight graph response for chat_id=%s: %s...",
        chat_id,
        response_message[:100] if response_message else "(empty)",
    )

    # Check if agent handed back to supervisor
    all_messages = result.get("messages", [])
    hand_back = detect_hand_back_tool(all_messages)
    if hand_back:
        logger.info(
            "Flight agent handed back to supervisor: %s", hand_back.get("reason")
        )
        return {
            "message": response_message,
            "type": "hand_back",
            "signal": "hand_back",
            "reason": hand_back.get("reason", ""),
            "is_detour": hand_back.get("is_detour", False),
            "flight": result.get("flight", {}),
            "message_id": message_id,
        }

    # Check if flight search was performed THIS TURN and extract results for frontend
    # Only check new messages (after msg_count_before) to avoid returning stale results
    # from previous searches in the same conversation
    new_messages = (
        all_messages[msg_count_before:] if msg_count_before > 0 else all_messages
    )

    multicity_results = _extract_multicity_flight_search_results(new_messages)
    if multicity_results:
        logger.info(
            "Multicity flight search completed - returning %d legs for frontend",
            len(multicity_results["data"].get("multicity_legs", [])),
        )
        collected = _extract_collected_flight_params(all_messages)
        return {
            "message": response_message,
            "type": "multicity_flight_search_results",
            "signal": "done",
            "data": multicity_results["data"],
            "collected_params": collected,
            "flight": result.get("flight", {}),
            "message_id": message_id,
        }

    flight_results = _extract_flight_search_results(new_messages)

    if flight_results:
        # Return flight search results in frontend-expected format
        logger.info(
            "Flight search completed - returning %d flights for frontend",
            len(flight_results.get("flights", [])),
        )
        return {
            "message": response_message,
            "type": "flight_search_results",
            "signal": "done",
            "data": flight_results["data"],
            "flights": flight_results["flights"],
            "session_id": flight_results.get(
                "session_id", ""
            ),  # Use FlightLogic session_id from search (required for revalidation)
            "origin_location": flight_results.get("origin_location"),
            "destination_location": flight_results.get("destination_location"),
            "flight": result.get("flight", {}),
            "message_id": message_id,  # For frontend feedback
        }

    # Check for date-range flight search results
    date_range_results = _extract_flight_date_range_results(new_messages)
    if date_range_results:
        logger.info(
            "Date-range flight search completed — %d dates searched",
            len(date_range_results.get("dates", [])),
        )
        return {
            "message": response_message,
            "type": "flight_date_range_results",
            "signal": "done",
            "data": date_range_results,
            "flight": result.get("flight", {}),
            "message_id": message_id,
        }

    # No flight results - check for airport suggestions
    airport_suggestions = _extract_airport_suggestions(new_messages)

    if airport_suggestions:
        logger.info(
            "Airport disambiguation - returning %d suggestions for frontend",
            len(airport_suggestions),
        )

    return {
        "message": response_message,
        "type": result.get("response_type", "flight_conversation"),
        "data": result.get("response_data"),
        "suggestions": airport_suggestions,  # Top-level for ChatResponse.data.suggestions
        "flight": result.get("flight", {}),
        "message_id": message_id,  # For frontend feedback
    }


def cleanup_graph() -> None:
    """Clean up graph resources.

    Call this during application shutdown to properly close
    the MongoDB connection used by the checkpointer.
    """
    global _checkpointer, _mongo_client, _compiled_graph

    if _mongo_client is not None:
        logger.info("Closing LangGraph MongoDB client")
        _mongo_client.close()
        _mongo_client = None
        _checkpointer = None
        _compiled_graph = None


__all__ = [
    "cleanup_graph",
    "get_flight_graph",
    "get_flight_inner_agent",
    "invoke_flight_graph",
    "process_flight_messages",
]
