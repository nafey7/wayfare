"""LangGraph itinerary planning agent (V2).

Replaces the rigid 5-stage supervisor pipeline with a dynamic ReAct agent.
Uses create_agent with smart tools and middleware for trip planning.
The agent reasons about next steps based on conversation context — no
hardcoded stage sequence.

MongoDB checkpointer provides conversation state persistence using
chat_id as thread_id.
"""

import json
import logging
import time
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.ai.graph.base import create_agent_engine, create_checkpointer
from app.ai.graph.constants import TRIP_FIELDS
from app.ai.graph.suggestion_chips import parse_suggestions
from app.ai.graph.tools import (
    generate_itinerary,
    hand_back_to_supervisor,
    parse_dates,
    update_trip_info,
)
from app.ai.graph.tracing import generate_message_id, traced_observation
from app.ai.graph.utils import (
    detect_hand_back_tool,
    extract_last_ai_message,
)
from app.domains.user_preferences.repository import get_preferences
from app.domains.user_preferences.schemas import UserPreferencesResponse

logger = logging.getLogger(__name__)

# Module-level singletons
_itinerary_checkpointer: MongoDBSaver | None = None
_itinerary_mongo_client: MongoClient[dict[str, Any]] | None = None
_itinerary_compiled_graph: Any = None
_itinerary_inner_agent: Any = None


def format_travel_style_preferences(prefs: UserPreferencesResponse) -> str:
    """Format travel_style preferences as context for itinerary generation.

    Returns empty string if no preferences are set.
    """
    if not prefs.document_exists:
        return ""

    ts = prefs.travel_style
    parts: list[str] = []
    if ts.travel_pace:
        parts.append(f"- Travel pace: {ts.travel_pace}")
    if ts.budget_mindset:
        parts.append(f"- Budget mindset: {ts.budget_mindset}")
    if ts.accommodation:
        parts.append(f"- Accommodation preference: {ts.accommodation}")
    if ts.activity_density:
        parts.append(f"- Activity density: {ts.activity_density}")
    if ts.primary_goals:
        parts.append(f"- Primary interests: {', '.join(ts.primary_goals)}")
    if ts.getting_around:
        parts.append(f"- Getting around: {', '.join(ts.getting_around)}")

    if not parts:
        return ""

    return (
        "[USER TRAVEL PREFERENCES]\n"
        + "\n".join(parts)
        + "\n\nPersonalize the itinerary to match these preferences. "
        "Align activity pace, budget level, accommodation suggestions, "
        "and transport recommendations accordingly."
    )


_ITINERARY_TOOLS = [
    parse_dates,
    update_trip_info,
    generate_itinerary,
    hand_back_to_supervisor,
]


def _get_formatted_prompt() -> str:
    """Get the system prompt from Langfuse with fallback to hardcoded."""
    from app.ai.prompt_management import get_itinerary_agent_prompt

    return get_itinerary_agent_prompt()


def _create_itinerary_engine(checkpointer: MongoDBSaver | None = None) -> Any:
    """Create itinerary agent engine with static prompt (V1 standalone path)."""
    return create_agent_engine(
        tools=_ITINERARY_TOOLS,
        component="agent_itinerary",
        prompt_fn=_get_formatted_prompt,
        checkpointer=checkpointer,
        run_limit=15,
        # 10 covers the typical flow with retries:
        # parse_dates (×2 max) + generate_itinerary (×2 max)
        # plus headroom for update_trip_info calls and unexpected retries.
        # (Phase 1 O8: estimate_budget removed — BudgetSnapshot is already in
        # the structured itinerary output.)
        tool_call_limit=10,
    )


def get_itinerary_inner_agent() -> Any:
    """Get stateless itinerary agent engine for V2 supervisor (dynamic prompt).

    Uses ``dynamic_prompt_enabled=True`` so the system prompt is fetched fresh
    from Langfuse on every invocation via ``PromptContext``.
    """
    global _itinerary_inner_agent
    if _itinerary_inner_agent is None:
        logger.info("Creating stateless itinerary inner agent for V2 supervisor")
        _itinerary_inner_agent = create_agent_engine(
            tools=_ITINERARY_TOOLS,
            component="agent_itinerary",
            dynamic_prompt_enabled=True,
            run_limit=15,
            # 10 covers the typical flow with retries (Phase 1 O8). See
            # comment on _create_itinerary_engine above.
            tool_call_limit=10,
        )
    return _itinerary_inner_agent


def get_itinerary_graph() -> Any:
    """Get compiled itinerary graph with MongoDB checkpointer (singleton).

    V1 path — standalone graph with its own checkpointer.
    """
    global _itinerary_compiled_graph, _itinerary_checkpointer, _itinerary_mongo_client

    if _itinerary_compiled_graph is None:
        logger.info("Creating itinerary agent graph with MongoDB checkpointer")
        _itinerary_checkpointer, _itinerary_mongo_client = create_checkpointer(
            "itinerary"
        )
        _itinerary_compiled_graph = _create_itinerary_engine(
            checkpointer=_itinerary_checkpointer
        )

    return _itinerary_compiled_graph


async def invoke_itinerary_graph(
    message: str,
    user_id: str,
    chat_id: str,
    user_email: str | None = None,
    intent_name: str = "create_itinerary",
    context_hint: str | None = None,
) -> dict[str, Any]:
    """Invoke the itinerary graph for a user message.

    Main entry point for ChatService integration. The graph automatically
    loads previous state from MongoDB using chat_id as thread_id.

    Args:
        message: User's message text
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (used as thread_id for checkpointing)
        user_email: Optional user email for Langfuse tracing
        intent_name: Intent name for response metadata

    Returns:
        Dict containing:
        - message: AI response text
        - type: Response type for frontend rendering
        - intent_name: Intent identifier
        - message_id: Message ID for feedback correlation
        - response_time: Time taken in seconds
    """
    start_time = time.time()
    message_id = generate_message_id()

    try:
        graph = get_itinerary_graph()
    except Exception:
        logger.exception("Failed to create itinerary graph")
        return {
            "message": "I'd love to help plan your trip! Could you try again?",
            "type": "fallback_response",
            "intent_name": intent_name,
            "message_id": message_id,
            "response_time": time.time() - start_time,
        }

    config: dict[str, Any] = {
        "configurable": {"thread_id": chat_id, "user_id": user_id}
    }

    # Fetch user travel preferences to personalize itinerary generation.
    prefs_context = ""
    try:
        prefs = await get_preferences(user_id)
        prefs_context = format_travel_style_preferences(prefs)
    except Exception:
        logger.debug("Could not fetch user preferences for %s", user_id)

    # context_hint (from supervisor on agent switch) is a SystemMessage so user
    # content cannot escape into the context bracket (prompt injection prevention).
    messages: list[Any] = []
    if context_hint:
        messages.append(SystemMessage(content=context_hint))
    if prefs_context:
        messages.append(SystemMessage(content=prefs_context))
    messages.append(HumanMessage(content=message))
    input_state: dict[str, Any] = {
        "messages": messages,
        "user_id": user_id,
        "chat_id": chat_id,
    }

    with traced_observation(
        message_id=message_id,
        session_id=chat_id,
        user_id=user_id,
        user_email=user_email,
        name="itinerary-agent",
    ) as (_, callbacks, trace_metadata):
        if callbacks:
            config["callbacks"] = callbacks
        if trace_metadata:
            config["metadata"] = trace_metadata

        try:
            result = await graph.ainvoke(input_state, config)
        except Exception:
            logger.exception(
                "Itinerary graph invocation failed for chat_id=%s", chat_id
            )
            return {
                "message": "I encountered an issue while planning. Could you try again?",
                "type": "fallback_response",
                "intent_name": intent_name,
                "message_id": message_id,
                "response_time": time.time() - start_time,
            }

    all_messages = result.get("messages", [])

    response_message = extract_last_ai_message(all_messages)
    if not response_message:
        response_message = (
            "I'd love to help plan your trip! Tell me where you'd like to go and when."
        )

    response_time = time.time() - start_time

    # V1 path only: keyword-based booking intent detection.
    # V2 supervisor uses unified state — the itinerary agent's LLM signals
    # planning_complete via hand_back_to_supervisor, no keyword matching needed.
    booking_plan = _detect_booking_intent_v1(message, all_messages, result)
    if booking_plan:
        cross_data = _extract_cross_agent_data(result)
        logger.info(
            "Itinerary planning complete — booking_plan=%s, cross_data_keys=%s",
            booking_plan,
            list(cross_data.keys()),
        )
        return {
            "message": response_message,
            "type": "planning_complete",
            "signal": "done",
            "done_reason": "planning_complete",
            "booking_plan": booking_plan,
            "cross_agent_data": cross_data,
            "intent_name": intent_name,
            "message_id": message_id,
            "response_time": response_time,
        }

    # Check if agent handed back to supervisor (topic change or detour)
    hand_back = detect_hand_back_tool(all_messages)
    if hand_back:
        logger.info(
            "Itinerary agent handed back to supervisor: %s",
            hand_back.get("reason"),
        )
        return {
            "message": response_message,
            "type": "hand_back",
            "signal": "hand_back",
            "reason": hand_back.get("reason", ""),
            "is_detour": hand_back.get("is_detour", False),
            "itinerary": result.get("itinerary", {}),
            "message_id": message_id,
        }

    # Always include itinerary state so supervisor can accumulate shared_context
    response: dict[str, Any] = {
        "message": response_message,
        "type": "message",
        "intent_name": intent_name,
        "message_id": message_id,
        "response_time": response_time,
    }
    itinerary_data = result.get("itinerary", {})
    if itinerary_data:
        response["itinerary"] = itinerary_data
    return response


def process_itinerary_messages(
    all_messages: list[Any],
    message_id: str = "",
    preferences_summary: str = "",
    new_messages: list[Any] | None = None,
) -> dict[str, Any]:
    """Process itinerary agent messages into a response dict.

    Shared between V1 invoke_itinerary_graph and V2 supervisor dispatch.
    Handles hand_back detection and booking intent (via tool signals, not keywords).

    For V2: detects planning_complete hand_back and extracts cross_agent_data
    from update_trip_info ToolMessages so supervisor can populate shared_context.

    Args:
        all_messages: Full message history (for cross_agent_data, hand_back).
        new_messages: Messages from the current dispatch only. When provided,
            generate_itinerary tool results are only detected in these messages.
            This prevents MODE 2 text replies from being wrapped as
            itinerary_results just because a prior generation exists in history.
    """
    hand_back = detect_hand_back_tool(all_messages)
    if hand_back:
        response_message = extract_last_ai_message(all_messages)
        reason = hand_back.get("reason", "")

        # V2: Detect planning_complete hand_back
        # Match "planning_complete" (expected format from prompt) or
        # "book flight"/"book hotel" (fallback if LLM omits prefix).
        # Avoid bare "book" to prevent false positives ("recommend a book").
        reason_lower = reason.lower()
        is_planning_complete = "planning_complete" in reason_lower or any(
            f"book {agent}" in reason_lower
            for agent in ("flight", "hotel", "everything")
        )
        if is_planning_complete:
            cross_data = _extract_cross_agent_data_from_messages(all_messages)
            booking_plan = _parse_booking_plan_from_reason(reason)
            return {
                "message": response_message,
                "type": "hand_back",
                "signal": "done",
                "done_reason": "planning_complete",
                "booking_plan": booking_plan,
                "cross_agent_data": cross_data,
                "reason": reason,
                "is_detour": False,
                "message_id": message_id,
            }

        # Include cross_agent_data so shared_context captures trip params
        # even during hand_back (needed for detour return).
        cross_data = _extract_cross_agent_data_from_messages(all_messages)
        resp: dict[str, Any] = {
            "message": response_message,
            "type": "hand_back",
            "signal": "hand_back",
            "reason": reason,
            "is_detour": hand_back.get("is_detour", False),
            "message_id": message_id,
        }
        if cross_data:
            resp["cross_agent_data"] = cross_data
        return resp

    response_message = extract_last_ai_message(all_messages)
    if not response_message:
        response_message = (
            "I'd love to help plan your trip! Tell me where you'd like to go and when."
        )

    # Always extract cross_agent_data so supervisor captures context early
    cross_data = _extract_cross_agent_data_from_messages(all_messages)

    # Check if itinerary was generated — look for generate_itinerary tool result.
    # The tool uses response_format="content_and_artifact": the full itinerary dict
    # is stored in ToolMessage.artifact (never sent to the LLM); ToolMessage.content
    # holds only a compact summary string that the agent sees.
    # When new_messages is provided, only scan those (current dispatch) so that
    # MODE 2 text replies don't pick up the prior generation's artifact.
    structured_itinerary: dict[str, Any] | None = None
    itinerary_tool_destination: str | None = None
    itinerary_scan_messages = new_messages if new_messages is not None else all_messages
    for msg in itinerary_scan_messages:
        if isinstance(msg, ToolMessage) and msg.name == "generate_itinerary":
            has_artifact = bool(msg.artifact and isinstance(msg.artifact, dict))
            # Primary path: read artifact (set by content_and_artifact response_format)
            if has_artifact:
                structured_itinerary = msg.artifact
            # Fallback: legacy messages stored itinerary inline in content JSON
            if structured_itinerary is None:
                try:
                    content = (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                    tool_result = json.loads(content)
                    if tool_result.get("status") == "success":
                        structured_itinerary = tool_result.get("itinerary")
                except (json.JSONDecodeError, TypeError):
                    pass
            # Extract destination from content regardless of path
            try:
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                itinerary_tool_destination = json.loads(content).get("destination")
            except (json.JSONDecodeError, TypeError):
                pass

    if structured_itinerary:
        trip_type = "round_trip" if cross_data.get("return_date") else "one_way"
        # Build a short summary — the full itinerary renders as cards in the frontend.
        # Avoids showing the full markdown text that the LLM generated inline.
        # Derive num_days from itineraryItems length (not a schema field).
        itinerary_items = structured_itinerary.get("itineraryItems", [])
        num_days = len(itinerary_items) if itinerary_items else ""
        destination = cross_data.get("destination") or ""
        days_str = f"{num_days}-day " if num_days else ""
        dest_str = (
            f"{' '.join(w if w.isupper() else w.title() for w in destination.split())} "
            if destination
            else ""
        )

        # Personalize the chat message with the user's stated interests for
        # this trip (e.g. "food and culture", "adventure", "family") so they
        # can confirm preferences were honored without clicking the cards.
        # Falls back to stored profile preferences when no per-trip interests.
        trip_interests = cross_data.get("interests") or []
        if isinstance(trip_interests, list) and trip_interests:
            interests_phrase = (
                trip_interests[0]
                if len(trip_interests) == 1
                else " & ".join([", ".join(trip_interests[:-1]), trip_interests[-1]])
            )
            theme_note = f", with a focus on {interests_phrase}"
        elif preferences_summary:
            theme_note = f", personalized for your {preferences_summary} preferences"
        else:
            theme_note = ""

        summary_message = (
            f"Here's your {days_str}{dest_str}itinerary{theme_note}! "
            f"The plan is displayed as interactive cards above. "
            f"Let me know if you'd like to change anything, or say "
            f"'book flights', 'book hotels', or 'book everything' when you're ready!"
        )

        # Parse LLM-generated suggestions from the original AI response
        # (summary_message replaces the LLM text, so extract suggestions first).
        # Fall back to sensible defaults if the LLM didn't provide any.
        _, llm_suggestions = parse_suggestions(response_message or "")
        if not llm_suggestions:
            dest = destination or "your destination"
            llm_suggestions = [
                {
                    "title": f"Find flights to {dest}",
                    "command": f"Find flights to {dest}",
                },
                {
                    "title": f"Find hotels in {dest}",
                    "command": f"Find hotels in {dest}",
                },
                {
                    "title": "Modify the itinerary",
                    "command": "Can you adjust the itinerary?",
                },
            ]
        # Build response matching V1 supervisor shape so frontend receives
        # identical JSON regardless of which supervisor version is active.
        # V1 puts structured_itinerary inside data.metadata; ChatService V2
        # reads response["metadata"] and passes it as ChatResponse.data.
        itinerary_response: dict[str, Any] = {
            "message": summary_message,
            "type": "itinerary_results",
            "signal": "done",
            "message_id": message_id,
            "suggestions": llm_suggestions if llm_suggestions else None,
            "metadata": {
                "structured_itinerary": structured_itinerary,
            },
            "origin": cross_data.get("origin"),
            "destination": cross_data.get("destination") or itinerary_tool_destination,
            "origin_iata": cross_data.get("origin_iata"),
            "destination_iata": cross_data.get("destination_iata"),
            "origin_name": cross_data.get("origin_name"),
            "destination_name": cross_data.get("destination_name"),
            "departure_date": cross_data.get("departure_date"),
            "return_date": cross_data.get("return_date"),
            "adults": cross_data.get("adults"),
            "children": cross_data.get("children"),
            "infants": cross_data.get("infants"),
            "trip_type": trip_type,
        }
        return itinerary_response

    response: dict[str, Any] = {
        "message": response_message,
        "type": "message",
        "message_id": message_id,
    }
    if cross_data:
        response["cross_agent_data"] = cross_data
    return response


def _extract_cross_agent_data_from_messages(messages: list[Any]) -> dict[str, Any]:
    """Extract trip data from itinerary agent messages.

    Scans update_trip_info tool results AND generate_itinerary tool call
    arguments to build a consolidated cross-agent data dict. The agent may
    not always call update_trip_info, but generate_itinerary always receives
    destination, dates, and passengers as arguments.

    Args:
        messages: List of LangChain messages from itinerary agent

    Returns:
        Dict with trip data for shared_context["trip"]
    """
    cross_data: dict[str, Any] = {}

    for msg in messages:
        # Source 1: update_trip_info tool results (most authoritative)
        if isinstance(msg, ToolMessage) and msg.name == "update_trip_info":
            try:
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                result = json.loads(content)
                trip_info = result.get("trip_info", result)

                for field in TRIP_FIELDS:
                    if trip_info.get(field):
                        cross_data[field] = trip_info[field]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        # Source 2: generate_itinerary tool call args
        # These always contain destination, dates, passengers even when
        # update_trip_info was not called.
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get("name") == "generate_itinerary":
                    args = tc.get("args", {})
                    for field in TRIP_FIELDS:
                        if args.get(field) and field not in cross_data:
                            cross_data[field] = args[field]

    # Build hotel_cities from destination data
    dest = cross_data.get("destination")
    dest_country = cross_data.get("destination_country")
    if dest and cross_data.get("departure_date"):
        cross_data["hotel_cities"] = [
            {
                "city": dest,
                "country": dest_country or "",
                "checkin": cross_data.get("departure_date", ""),
                "checkout": cross_data.get("return_date", ""),
            }
        ]

    return cross_data


def _parse_booking_plan_from_reason(reason: str) -> list[str]:
    """Parse booking plan from hand_back reason text.

    The itinerary agent includes booking intent in the reason string.
    Default to ["flight", "hotel"] if we can't parse specifics.

    Args:
        reason: The hand_back reason text from the agent

    Returns:
        Booking plan list (e.g., ["flight", "hotel"])
    """
    reason_lower = reason.lower()

    # Check for specific agent mentions
    has_flight = "flight" in reason_lower
    has_hotel = "hotel" in reason_lower

    if has_flight and has_hotel:
        # Check order preference
        if "hotel" in reason_lower and reason_lower.index("hotel") < reason_lower.index(
            "flight"
        ):
            return ["hotel", "flight"]
        return ["flight", "hotel"]
    if has_flight:
        return ["flight"]
    if has_hotel:
        return ["hotel"]

    # Default: book both, flights first
    return ["flight", "hotel"]


def _extract_cross_agent_data(result: dict[str, Any]) -> dict[str, Any]:
    """Extract trip data from itinerary state for cross-agent pre-fill.

    Used by V1 invoke path. V2 supervisor doesn't need this — the shared
    message history IS the cross-agent data.

    Returns:
        Dict with origin/destination IATA codes, dates, passengers,
        and hotel cities for downstream agents.
    """
    itinerary = result.get("itinerary", {})
    cross_data: dict[str, Any] = {}

    if itinerary.get("origin_iata"):
        cross_data["origin_iata"] = itinerary["origin_iata"]
    if itinerary.get("destination_iata"):
        cross_data["destination_iata"] = itinerary["destination_iata"]
    if itinerary.get("departure_date"):
        cross_data["departure_date"] = itinerary["departure_date"]
    if itinerary.get("return_date"):
        cross_data["return_date"] = itinerary["return_date"]
    if itinerary.get("adults"):
        cross_data["adults"] = itinerary["adults"]
    if itinerary.get("children"):
        cross_data["children"] = itinerary["children"]

    # Build hotel_cities from destination + dates
    dest = itinerary.get("destination")
    dest_country = itinerary.get("destination_country")
    if dest and itinerary.get("departure_date"):
        cross_data["hotel_cities"] = [
            {
                "city": dest,
                "country": dest_country or "",
                "checkin": itinerary.get("departure_date", ""),
                "checkout": itinerary.get("return_date", ""),
            }
        ]

    return cross_data


def _detect_booking_intent_v1(
    user_message: str,
    messages: list[Any],
    result: dict[str, Any],
) -> list[str] | None:
    """V1 only: Detect booking intent via keywords.

    Deprecated for V2 — the itinerary agent's LLM handles booking intent
    detection as part of its normal reasoning and signals planning_complete.

    Returns:
        Booking plan list (e.g., ["flight", "hotel"]) or None
    """
    msg_lower = user_message.lower()

    book_all_keywords = [
        "book everything",
        "book it all",
        "make it happen",
        "let's book",
        "book the trip",
        "book this",
        "go ahead and book",
    ]
    book_flight_keywords = [
        "book the flight",
        "book flights",
        "now book flights",
        "now book the flight",
        "just the flight",
        "only flights",
    ]
    book_hotel_keywords = [
        "book the hotel",
        "book hotels",
        "now book hotels",
        "now book the hotel",
        "just the hotel",
        "only hotel",
    ]

    plan: list[str] | None = None

    if any(kw in msg_lower for kw in book_all_keywords):
        plan = ["flight", "hotel"]
    elif any(kw in msg_lower for kw in book_flight_keywords):
        plan = ["flight"]
    elif any(kw in msg_lower for kw in book_hotel_keywords):
        plan = ["hotel"]

    if plan is None:
        return None

    itinerary = result.get("itinerary", {})
    has_destination = bool(
        itinerary.get("destination") or itinerary.get("destination_iata")
    )
    has_dates = bool(itinerary.get("departure_date"))

    has_generated_itinerary = result.get("planning_result") is not None
    if not has_generated_itinerary:
        for msg in messages:
            if isinstance(msg, ToolMessage) and msg.name == "generate_itinerary":
                has_generated_itinerary = True
                break

    if not (has_destination and has_dates) and not has_generated_itinerary:
        return None

    hotel_first_keywords = ["hotel first", "hotels first", "hotel then flight"]
    if any(kw in msg_lower for kw in hotel_first_keywords) and plan == [
        "flight",
        "hotel",
    ]:
        plan = ["hotel", "flight"]

    return plan


def cleanup_itinerary_graph() -> None:
    """Clean up itinerary graph resources.

    Call this during application shutdown to properly close
    the MongoDB connection used by the checkpointer.
    """
    global _itinerary_checkpointer, _itinerary_mongo_client, _itinerary_compiled_graph

    if _itinerary_mongo_client is not None:
        logger.info("Closing itinerary LangGraph MongoDB client")
        _itinerary_mongo_client.close()
        _itinerary_mongo_client = None
        _itinerary_checkpointer = None
        _itinerary_compiled_graph = None


__all__ = [
    "cleanup_itinerary_graph",
    "get_itinerary_graph",
    "get_itinerary_inner_agent",
    "invoke_itinerary_graph",
    "process_itinerary_messages",
]
