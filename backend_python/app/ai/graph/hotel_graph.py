"""LangGraph hotel booking agent.

This module creates and manages the ReAct agent for hotel booking conversations.
Uses MongoDB checkpointer for conversation state persistence.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from app.ai.graph.base import create_agent_engine, create_checkpointer
from app.ai.graph.state import HotelState
from app.ai.graph.suggestion_chips import parse_suggestions
from app.ai.graph.tools import (
    hand_back_to_supervisor,
    parse_dates,
    resolve_city,
    search_hotels,
)
from app.ai.graph.tracing import generate_message_id, traced_observation
from app.ai.graph.utils import (
    build_hand_back_response,
    detect_hand_back_tool,
    extract_last_ai_message,
    extract_text_content,
)

logger = logging.getLogger(__name__)

# Module-level singletons for efficiency
_hotel_checkpointer: MongoDBSaver | None = None
_hotel_mongo_client: MongoClient[dict[str, Any]] | None = None
_hotel_compiled_graph: Any = None
_hotel_inner_agent: Any = None


def _get_formatted_prompt() -> str:
    """Get the system prompt from Langfuse with fallback to hardcoded."""
    from app.ai.prompt_management import get_hotel_prompt

    return get_hotel_prompt()


# NOTE (issue #1034): `select_hotel` is intentionally dropped from the agent's
# tool list. Hotel booking is initiated from the frontend by clicking a hotel
# card — the chat-based "book option N" flow is deprecated. The agent should
# direct users to click the Book button instead of trying to handle selection.
_HOTEL_TOOLS = [
    resolve_city,
    parse_dates,
    search_hotels,
    hand_back_to_supervisor,
]


def _create_hotel_engine(
    checkpointer: MongoDBSaver | None = None,
    state_schema: type | None = None,
) -> Any:
    """Create hotel agent engine with static prompt (V1 standalone path)."""
    return create_agent_engine(
        tools=_HOTEL_TOOLS,
        component="agent_hotel",
        prompt_fn=_get_formatted_prompt,
        checkpointer=checkpointer,
        state_schema=state_schema,
    )


def get_hotel_inner_agent() -> Any:
    """Get stateless hotel agent engine for V2 supervisor (dynamic prompt).

    Uses ``dynamic_prompt_enabled=True`` so the system prompt is fetched fresh
    from Langfuse on every invocation via ``PromptContext``.
    """
    global _hotel_inner_agent
    if _hotel_inner_agent is None:
        logger.info("Creating stateless hotel inner agent for V2 supervisor")
        _hotel_inner_agent = create_agent_engine(
            tools=_HOTEL_TOOLS,
            component="agent_hotel",
            dynamic_prompt_enabled=True,
        )
    return _hotel_inner_agent


def get_hotel_graph() -> Any:
    """Get compiled hotel graph with MongoDB checkpointer (singleton).

    V1 path — standalone graph with its own checkpointer and HotelState schema.
    """
    global _hotel_compiled_graph, _hotel_checkpointer, _hotel_mongo_client

    if _hotel_compiled_graph is None:
        logger.info("Creating hotel graph with MongoDB checkpointer")
        _hotel_checkpointer, _hotel_mongo_client = create_checkpointer("hotel")
        _hotel_compiled_graph = _create_hotel_engine(
            checkpointer=_hotel_checkpointer, state_schema=HotelState
        )

    return _hotel_compiled_graph


def process_hotel_messages(
    all_messages: list[Any],
    msg_count_before: int = 0,
    message_id: str = "",
) -> dict[str, Any]:
    """Process hotel agent messages into a response dict.

    Shared between V1 invoke_hotel_graph and V2 supervisor dispatch.
    Handles hand_back detection, hotel search results, and booking redirect.
    """
    hand_back = detect_hand_back_tool(all_messages)
    if hand_back:
        resp = build_hand_back_response(all_messages, hand_back, message_id)
        # Preserve collected params so shared_context captures hotel data
        # even during hand_back (needed for detour return).
        collected = _extract_collected_hotel_params(all_messages)
        if collected:
            resp["collected_params"] = collected
        return resp

    response_message = extract_last_ai_message(all_messages)

    # Check for booking redirect (user selected a hotel)
    booking_redirect = _extract_hotel_booking_redirect(all_messages)
    if booking_redirect:
        redirect_url = booking_redirect["redirect_url"]
        selected_hotel = booking_redirect.get("selected_hotel", "your selected hotel")
        formatted_message = (
            f"Great choice! Click here -> [Complete Your Booking]({redirect_url}) "
            f"to add your guest details and finalize your reservation for {selected_hotel}."
        )
        return {
            "message": formatted_message,
            "type": "hotel_booking_redirect",
            "redirect_url": redirect_url,
            "action_button_text": "Complete Booking",
            "action_button_url": redirect_url,
            "selected_hotel": selected_hotel,
            "selected_option": booking_redirect.get("selected_option", 0),
            "message_id": message_id,
        }

    # Check for hotel search results (only new messages to avoid stale results)
    new_messages = (
        all_messages[msg_count_before:] if msg_count_before > 0 else all_messages
    )
    hotel_results = _extract_hotel_search_results(new_messages)

    if hotel_results:
        logger.info(
            "Hotel search completed - returning %d hotels",
            len(hotel_results.get("hotels", [])),
        )
        # Extract search params from messages
        search_params = _extract_search_params_from_messages(all_messages)
        hotel_data = hotel_results.get("data", {})
        if isinstance(hotel_data, dict):
            hotel_data["search_params"] = search_params

        collected = _extract_collected_hotel_params(all_messages)
        # Parse LLM suggestions; fall back to defaults for search results
        cleaned_msg, hotel_suggestions = parse_suggestions(response_message or "")
        if not hotel_suggestions:
            dest = (collected or {}).get("city", "your destination")
            hotel_suggestions = [
                {
                    "title": f"Find flights to {dest}",
                    "command": f"Find flights to {dest}",
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
            "type": "hotel_search_results",
            "signal": "done",
            "data": hotel_data,
            "hotels": hotel_results["hotels"],
            "session_id": hotel_results["session_id"],
            "collected_params": collected,
            "suggestions": hotel_suggestions,
            "message_id": message_id,
        }

    # If the tool returned no_results with suggestions, use the tool's
    # message directly so the neighbourhood/filter advice reaches the user.
    no_results_msg = _extract_hotel_no_results_message(new_messages)
    if no_results_msg:
        response_message = no_results_msg

    collected = _extract_collected_hotel_params(all_messages)
    return {
        "message": response_message,
        "type": "hotel_conversation",
        "collected_params": collected,
        "message_id": message_id,
    }


def _extract_collected_hotel_params(messages: list[Any]) -> dict[str, Any]:
    """Extract collected hotel parameters from tool messages.

    Scans resolve_city, parse_dates, and search_hotels tool results to build
    a dict of collected hotel params for shared_context. Extracting from
    pre-search tools (resolve_city, parse_dates) ensures params are captured
    even when a detour hand_back happens before search.

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with collected hotel params (city, country, checkin, checkout, adults)
    """
    params: dict[str, Any] = {}

    for msg in messages:
        # Extract from resolve_city tool results (available before search)
        if isinstance(msg, ToolMessage) and msg.name == "resolve_city":
            try:
                content = msg.content
                result = json.loads(content) if isinstance(content, str) else content
                if result.get("status") == "resolved":
                    if result.get("city"):
                        params["city"] = result["city"]
                    if result.get("country"):
                        params["country"] = result["country"]
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Extract from parse_dates tool results (available before search)
        if isinstance(msg, ToolMessage) and msg.name == "parse_dates":
            try:
                content = msg.content
                result = json.loads(content) if isinstance(content, str) else content
                if result.get("departure_date"):
                    params["checkin"] = result["departure_date"]
                if result.get("return_date"):
                    params["checkout"] = result["return_date"]
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

        # Extract from search_hotels tool calls (overrides pre-search values)
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls or []:
                if tool_call.get("name") == "search_hotels":
                    args = tool_call.get("args", {})
                    if args.get("city_name"):
                        params["city"] = args["city_name"]
                    if args.get("country_name"):
                        params["country"] = args["country_name"]
                    if args.get("checkin"):
                        params["checkin"] = args["checkin"]
                    if args.get("checkout"):
                        params["checkout"] = args["checkout"]
                    if args.get("adults"):
                        params["adults"] = args["adults"]
                    if args.get("children"):
                        params["children"] = args["children"]
                    if args.get("rooms"):
                        params["rooms"] = args["rooms"]
                    if args.get("nearby_lat") is not None:
                        params["nearby_lat"] = args["nearby_lat"]
                    if args.get("nearby_lng") is not None:
                        params["nearby_lng"] = args["nearby_lng"]

    return params


def _extract_search_params_from_messages(messages: list[Any]) -> dict[str, Any]:
    """Extract search parameters from the tool call that triggered the search.

    Scans messages for the AIMessage containing the search_hotels tool call
    to extract the original search parameters.

    This is more reliable than relying on state, which may not be updated
    consistently across environments (e.g., staging vs local).

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with search parameters (destination_city, country, check_in_date, check_out_date, rooms, adults, children)
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tool_call in msg.tool_calls or []:
                if tool_call.get("name") == "search_hotels":
                    args = tool_call.get("args", {})
                    return {
                        "destination_city": args.get("city_name", ""),
                        "country": args.get("country_name", ""),
                        "check_in_date": args.get("checkin", ""),
                        "check_out_date": args.get("checkout", ""),
                        "rooms": args.get("rooms", 1),
                        "adults": args.get("adults"),
                        "children": args.get("children", 0),
                        # Filters
                        "price_min": args.get("price_min"),
                        "price_max": args.get("price_max"),
                        "min_rating": args.get("min_rating"),
                        "property_types": args.get("property_types"),
                        "refundable_only": args.get("refundable_only"),
                        "required_facilities": args.get("required_facilities"),
                        "max_distance_km": args.get("max_distance_km"),
                        "locality": args.get("locality"),
                        "nearby_lat": args.get("nearby_lat"),
                        "nearby_lng": args.get("nearby_lng"),
                    }
    return {}


def _extract_hotel_no_results_message(messages: list[Any]) -> str | None:
    """Extract a user-friendly no-results message from tool output.

    When the search_hotels tool returns status ``no_results``, the suggestion
    text (neighbourhood list, filter advice) should be shown to the user
    directly — not rewritten by the LLM which tends to drop details.

    Returns:
        A formatted message string, or None if no no-results tool output found.
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "search_hotels":
            try:
                content = msg.content
                if isinstance(content, str):
                    tool_result = json.loads(content)
                elif isinstance(content, dict):
                    tool_result = content
                else:
                    continue

                if tool_result.get("status") != "no_results":
                    continue

                message = tool_result.get("message", "No hotels found.")
                suggestion = tool_result.get("suggestion", "")
                if suggestion:
                    return f"{message} {suggestion}"
                return message
            except (json.JSONDecodeError, TypeError):
                continue
    return None


def _extract_hotel_search_results(messages: list[Any]) -> dict[str, Any] | None:
    """Extract hotel search results from tool messages.

    Scans messages for search_hotels tool output and transforms it
    into the frontend-expected format.

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with frontend-compatible hotel data, or None if no results found
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "search_hotels":
            try:
                # Issue #1034: full payload now lives on `msg.artifact`. The
                # LLM only saw the summary in msg.content; we read the artifact
                # to build the frontend payload.
                artifact = getattr(msg, "artifact", None)
                if not isinstance(artifact, dict):
                    continue

                summary = artifact.get("summary", {})
                hotels = artifact.get("hotels", []) or []
                session_id = artifact.get("session_id", "")

                return {
                    "data": {
                        "summary": {
                            "total_hotels": summary.get("total_found", 0),
                            "nights": summary.get("nights", 1),
                            "price_range": summary.get("price_range", {}),
                        },
                    },
                    "hotels": hotels,
                    "session_id": session_id,
                }

            except (KeyError, TypeError) as e:
                logger.warning("Failed to parse hotel search artifact: %s", e)
                continue

    return None


def _extract_hotel_booking_redirect(messages: list[Any]) -> dict[str, Any] | None:
    """Extract booking redirect from select_hotel tool output.

    Scans messages for select_hotel tool output that contains a redirect URL.

    Args:
        messages: List of LangGraph messages

    Returns:
        Dict with redirect data, or None if no redirect found
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and msg.name == "select_hotel":
            try:
                # Parse the tool output
                content = msg.content
                if isinstance(content, dict):
                    tool_result = content
                elif isinstance(content, str):
                    if not content or content.strip() == "":
                        continue
                    tool_result = json.loads(content)
                else:
                    tool_result = content

                # Check if this is a successful redirect
                if tool_result.get("status") != "redirect":
                    continue

                redirect_url = tool_result.get("redirect_url")
                if not redirect_url:
                    continue

                return {
                    "redirect_url": redirect_url,
                    "selected_hotel": tool_result.get("selected_hotel", ""),
                    "selected_option": tool_result.get("selected_option", 0),
                }

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning("Failed to parse hotel booking redirect: %s", e)
                continue

    return None


async def invoke_hotel_graph(
    message: str,
    user_id: str,
    chat_id: str,
    hotel_params: dict[str, Any] | None = None,
    user_email: str | None = None,
    context_hint: str | None = None,
) -> dict[str, Any]:
    """Invoke the hotel graph for a user message.

    This is the main entry point for the ChatService integration.
    The graph automatically loads previous state from MongoDB using
    chat_id as thread_id.

    Args:
        message: User's message text
        user_id: Authenticated user ID
        chat_id: Chat conversation ID (used as thread_id for checkpointing)
        hotel_params: Optional existing hotel parameters to merge
        user_email: Optional user email for Langfuse tracing

    Returns:
        Dict containing:
        - message: AI response text
        - type: Response type for frontend rendering
        - data: Optional additional data (hotel cards, etc.)
        - hotel: Updated hotel parameters
        - session_id: FlightLogic session ID (if search performed)
        - message_id: Message ID for feedback correlation
    """
    graph = get_hotel_graph()

    # Generate message_id for feedback correlation
    message_id = generate_message_id()

    # Check if hotel_params are complete (from supervisor/itinerary)
    hotel_params_dict = hotel_params or {}
    has_city = bool(hotel_params_dict.get("city"))
    has_checkin = bool(hotel_params_dict.get("checkin"))
    has_checkout = bool(hotel_params_dict.get("checkout"))
    params_complete = has_city and has_checkin and has_checkout

    # CRITICAL: Only override message on FIRST call (when no checkpoint history exists)
    # Check if this chat_id has existing state in checkpointer
    checkpointer = _hotel_checkpointer
    if checkpointer is None:
        get_hotel_graph()
        checkpointer = _hotel_checkpointer
    config_for_check = {"configurable": {"thread_id": chat_id}}
    existing_state = None
    msg_count_before = 0
    try:
        # Get the last checkpoint to see if conversation already started
        existing_state = checkpointer.get(config_for_check)
        if existing_state and existing_state.values:
            existing_messages = existing_state.values.get("messages", [])
            msg_count_before = len(existing_messages)
    except Exception as e:
        logger.debug("No existing checkpoint for thread_id=%s: %s", chat_id, e)

    # Only override message if: params complete AND no previous conversation
    if params_complete and not existing_state:
        logger.info(
            f"Hotel params pre-populated (FIRST call): city={hotel_params_dict.get('city')}, "
            f"checkin={hotel_params_dict.get('checkin')}, "
            f"checkout={hotel_params_dict.get('checkout')} - will search immediately"
        )
        # Override user message to trigger immediate search
        message = (
            f"Search hotels in {hotel_params_dict.get('city')} "
            f"from {hotel_params_dict.get('checkin')} to {hotel_params_dict.get('checkout')} "
            f"for {hotel_params_dict.get('adults', 2)} adults. "
            f"Use the pre-filled hotel parameters - don't ask me any questions."
        )
    elif params_complete and existing_state:
        logger.info(
            f"Hotel params complete but conversation exists - preserving user message: '{message[:50]}...'"
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
        "hotel": hotel_params_dict,
    }

    logger.debug(
        "Invoking hotel graph for chat_id=%s, message=%s...",
        chat_id,
        message[:50],
    )

    # Use traced_observation for Langfuse tracing with our message_id
    with traced_observation(
        message_id=message_id,
        session_id=chat_id,
        user_id=user_id,
        user_email=user_email,
        name="hotel-agent",
    ) as (_, callbacks, trace_metadata):
        # Config with thread_id enables automatic state loading/saving
        # user_id is also passed for tool injection (select_hotel needs it)
        config: dict[str, Any] = {
            "configurable": {"thread_id": chat_id, "user_id": user_id}
        }
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
                    "This happens when the agent stops before executing a tool call. "
                    "Clearing checkpoint state..."
                )

                # Clear the bad checkpoint state by deleting it
                try:
                    # Get the checkpointer and delete this thread's state
                    await graph.aupdate_state(
                        config,
                        values=None,  # Clear all state
                    )
                    logger.info("Cleared checkpoint state for chat_id=%s", chat_id)
                except Exception as clear_error:
                    logger.error(
                        f"Failed to clear checkpoint state: {clear_error}",
                        exc_info=True,
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
        "Hotel graph response for chat_id=%s: %s...",
        chat_id,
        response_message[:100] if response_message else "(empty)",
    )

    # Check if agent handed back to supervisor
    hand_back = detect_hand_back_tool(result.get("messages", []))
    if hand_back:
        logger.info(
            "Hotel agent handed back to supervisor: %s", hand_back.get("reason")
        )
        return {
            "message": response_message,
            "type": "hand_back",
            "signal": "hand_back",
            "reason": hand_back.get("reason", ""),
            "is_detour": hand_back.get("is_detour", False),
            "hotel": result.get("hotel", {}),
            "message_id": message_id,
        }

    # Check for booking redirect first (user selected a hotel)
    booking_redirect = _extract_hotel_booking_redirect(result.get("messages", []))

    if booking_redirect:
        # Return booking redirect for frontend
        redirect_url = booking_redirect["redirect_url"]
        selected_hotel = booking_redirect.get("selected_hotel", "your selected hotel")

        logger.info(
            "Hotel selection completed - returning redirect for %s",
            selected_hotel,
        )

        # Format message with markdown link (like legacy handler)
        formatted_message = (
            f"Great choice! Click here 👉 [Complete Your Booking]({redirect_url}) "
            f"to add your guest details and finalize your reservation for {selected_hotel}."
        )

        return {
            "message": formatted_message,
            "type": "hotel_booking_redirect",
            "redirect_url": redirect_url,
            "action_button_text": "Complete Booking",
            "action_button_url": redirect_url,
            "selected_hotel": selected_hotel,
            "selected_option": booking_redirect.get("selected_option", 0),
            "hotel": result.get("hotel", {}),
            "message_id": message_id,
        }

    # Check if hotel search was performed THIS TURN and extract results for frontend
    # Only check new messages (after msg_count_before) to avoid returning stale results
    all_messages = result.get("messages", [])
    new_messages = (
        all_messages[msg_count_before:] if msg_count_before > 0 else all_messages
    )
    hotel_results = _extract_hotel_search_results(new_messages)

    if hotel_results:
        # Return hotel search results in frontend-expected format
        logger.info(
            "Hotel search completed - returning %d hotels for frontend",
            len(hotel_results.get("hotels", [])),
        )

        # WORKAROUND: Extract search parameters from tool call messages instead of state.
        # When LANGFUSE_ENABLED=True, the `hotel` state field is lost during callback
        # processing (LangGraph bug with TypedDict fields without reducers).
        # See: https://github.com/myvoya/voya/issues/265
        search_params = _extract_search_params_from_messages(result.get("messages", []))

        # If extraction from messages failed, try state as fallback
        if not search_params or not search_params.get("destination_city"):
            hotel_params = result.get("hotel", {})
            search_params = {
                "destination_city": hotel_params.get("city", ""),
                "country": hotel_params.get("country", ""),
                "check_in_date": hotel_params.get("checkin", ""),
                "check_out_date": hotel_params.get("checkout", ""),
                "rooms": hotel_params.get("rooms", 1),
                "adults": hotel_params.get("adults"),
                "children": hotel_params.get("children", 0),
                "price_min": hotel_params.get("price_min"),
                "price_max": hotel_params.get("price_max"),
                "min_rating": hotel_params.get("min_rating"),
                "property_types": hotel_params.get("property_types"),
                "refundable_only": hotel_params.get("refundable_only"),
                "required_facilities": hotel_params.get("required_facilities"),
                "max_distance_km": hotel_params.get("max_distance_km"),
                "locality": hotel_params.get("locality"),
                "nearby_lat": hotel_params.get("nearby_lat"),
                "nearby_lng": hotel_params.get("nearby_lng"),
            }

        # Log extracted parameters for debugging
        logger.info(
            "Extracted search params: destination_city=%s, check_in=%s, check_out=%s, adults=%s",
            search_params.get("destination_city"),
            search_params.get("check_in_date"),
            search_params.get("check_out_date"),
            search_params.get("adults"),
        )

        # Add search_params to data if it exists
        hotel_data = hotel_results.get("data", {})
        if isinstance(hotel_data, dict):
            hotel_data["search_params"] = search_params

        return {
            "message": response_message,
            "type": "hotel_search_results",
            "signal": "done",
            "data": hotel_data,
            "hotels": hotel_results["hotels"],
            "session_id": hotel_results["session_id"],
            "hotel": result.get("hotel", {}),
            "message_id": message_id,
        }

    # If the tool returned no_results with suggestions, use the tool's
    # message directly so the neighbourhood/filter advice reaches the user.
    no_results_msg = _extract_hotel_no_results_message(new_messages)
    if no_results_msg:
        response_message = no_results_msg

    # No hotel results or redirect - return conversation response
    return {
        "message": response_message,
        "type": result.get("response_type", "hotel_conversation"),
        "data": result.get("response_data"),
        "hotel": result.get("hotel", {}),
        "message_id": message_id,
    }


def cleanup_hotel_graph() -> None:
    """Clean up hotel graph resources.

    Call this during application shutdown to properly close
    the MongoDB connection used by the checkpointer.
    """
    global _hotel_checkpointer, _hotel_mongo_client, _hotel_compiled_graph

    if _hotel_mongo_client is not None:
        logger.info("Closing hotel LangGraph MongoDB client")
        _hotel_mongo_client.close()
        _hotel_mongo_client = None
        _hotel_checkpointer = None
        _hotel_compiled_graph = None


__all__ = [
    "cleanup_hotel_graph",
    "get_hotel_graph",
    "get_hotel_inner_agent",
    "invoke_hotel_graph",
    "process_hotel_messages",
]
