"""Hotel booking tool for LangGraph hotel agent.

This tool handles hotel selection and generates booking redirect URLs.
It bridges the LangGraph agent with the existing booking infrastructure.
"""

import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HotelSelectionInput(BaseModel):
    """Input schema for hotel selection.

    Note: user_id and chat_id are injected from config, not provided by LLM.
    """

    selection: str = Field(
        description="User's selection text (e.g., '1', 'book option 2', 'cheapest', 'I'll take the first one')"
    )
    hotels: list[dict[str, Any]] = Field(
        description="List of hotels from the previous search_hotels call (the flat `hotels` array from the tool result)."
    )
    session_id: str = Field(
        description="FlightLogic session_id from the search_hotels result (required for booking)"
    )
    search_params: dict[str, Any] = Field(
        description="Original search parameters (city, country, checkin, checkout, rooms, adults, children)"
    )


@tool("select_hotel", args_schema=HotelSelectionInput)
async def select_hotel(
    selection: str,
    hotels: list[dict[str, Any]],
    session_id: str,
    search_params: dict[str, Any],
    # These are injected from config, not provided by LLM
    config: Annotated[RunnableConfig, InjectedToolArg],
) -> dict[str, Any]:
    """Handle hotel selection and generate booking redirect URL.

    Call this tool when the user wants to book a hotel from the search results.
    Pass the hotels list from your previous search_hotels call.

    Recognizes selection patterns like:
    - "book option 1", "book 2", "option 3"
    - "book the first one", "I'll take the second"
    - "book cheapest", "book best value", "book highest rated"
    - Just "1" or "2"

    Returns a redirect URL for the user to complete their booking.
    """
    from app.ai.utils import SelectionDomain, SelectionParser
    from app.core.config import settings
    from app.domains.booking_sessions.service import BookingSessionService

    # Extract user_id and chat_id from config (injected, not LLM-provided)
    configurable = config.get("configurable", {})
    user_id = configurable.get("user_id", "")
    chat_id = configurable.get("thread_id", "")  # thread_id is chat_id

    logger.info(
        f"select_hotel called: selection='{selection}', "
        f"hotels_count={len(hotels)}, session_id={session_id}, "
        f"user_id={user_id}, chat_id={chat_id}"
    )

    # Validate injected config values
    if not user_id or not chat_id:
        logger.error(
            f"Missing user_id or chat_id from config: user_id={user_id}, chat_id={chat_id}"
        )
        return {
            "status": "error",
            "error": "Session configuration error. Please try again.",
            "instruction": "Tell the user there was a technical issue and to try their search again.",
        }

    # Validate inputs
    if not hotels:
        return {
            "status": "error",
            "error": "No hotels provided. Make sure to pass the hotels from your previous search_hotels call.",
            "instruction": "Search for hotels first, then call select_hotel with those results.",
        }

    if not session_id:
        return {
            "status": "error",
            "error": "No session_id provided. Make sure to pass the session_id from your previous search_hotels call.",
            "instruction": "The session_id is required for booking. Search for hotels again if needed.",
        }

    # Parse user selection
    option_number = SelectionParser.parse(selection, SelectionDomain.HOTEL)

    if option_number is None:
        return {
            "status": "error",
            "error": f"Could not understand selection: '{selection}'",
            "instruction": "Ask the user to clarify which hotel they want to book (e.g., 'book option 1' or just '1').",
            "valid_range": f"1 to {len(hotels)}",
        }

    # Validate selection range
    if option_number < 1 or option_number > len(hotels):
        return {
            "status": "error",
            "error": f"Selection {option_number} is out of range. Only {len(hotels)} hotels available.",
            "instruction": f"Ask the user to select a number between 1 and {len(hotels)}.",
            "valid_range": f"1 to {len(hotels)}",
        }

    # Get selected hotel (convert from 1-based to 0-based index)
    selected_hotel = hotels[option_number - 1]
    hotel_name = selected_hotel.get("hotel_name", "Selected Hotel")

    logger.info(
        f"User selected hotel {option_number}: {hotel_name} (session: {session_id})"
    )

    # Ensure search_params has required occupancy fields with defaults
    # Use 'or' to handle None values (not just missing keys)
    adults = search_params.get("adults") or 2
    children = search_params.get("children") or 0
    rooms = search_params.get("rooms") or 1

    # Build room_configuration for frontend guest forms (required by hotel-booker)
    room_configuration = []
    adults_per_room = adults // rooms
    children_per_room = children // rooms
    extra_adults = adults % rooms
    extra_children = children % rooms

    for i in range(rooms):
        room_adults = adults_per_room + (1 if i < extra_adults else 0)
        room_children = children_per_room + (1 if i < extra_children else 0)
        room_configuration.append(
            {
                "room_no": i + 1,
                "adults": room_adults,
                "children": room_children,
            }
        )

    # Ensure search_params is complete for hotel-booker UI
    complete_search_params = {
        **search_params,
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "room_configuration": room_configuration,
    }

    logger.info(
        f"Built room_configuration: {room_configuration} "
        f"(rooms={rooms}, adults={adults}, children={children})"
    )

    # Store selection in booking session (for hotel-booker UI to retrieve)
    try:
        session_data = {
            "selected_hotel": selected_hotel,
            "search_params": complete_search_params,
            "selected_option": option_number,
            "booking_stage": "hotel_selected",
            "flightlogic_session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "source": "langgraph_agent",
            "status": "pending_guest_details",
        }

        await BookingSessionService.store_session(
            session_id=chat_id,  # Use chat_id as session_id for consistency
            user_id=user_id,
            session_data=session_data,
            ttl_hours=2,
        )

        logger.info(f"Stored booking session for chat_id: {chat_id}")

    except Exception as e:
        logger.error(f"Failed to store booking session: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Failed to prepare booking: {e}",
            "instruction": "Apologize for the error and ask if they'd like to try again.",
        }

    # Generate JWT auth token for hotel-booker UI
    try:
        import jwt

        payload = {
            "user_id": user_id,
            "session_id": chat_id,
            "type": "booking_auth",
            "exp": datetime.now(UTC).timestamp() + 1800,  # 30 minutes
        }

        booking_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        logger.info(f"Generated booking auth token for user {user_id}")

    except Exception as e:
        logger.warning(f"Failed to generate booking token: {e}")
        booking_token = None

    # Generate redirect URL
    base_url = settings.BACKEND_URL

    if booking_token:
        redirect_url = (
            f"{base_url}/dev/hotel-booker/index.html"
            f"?session_id={chat_id}&auth_token={booking_token}"
        )
    else:
        # Fallback without token (less secure)
        redirect_url = f"{base_url}/dev/hotel-booker/index.html?session_id={chat_id}"
        logger.warning("Generated redirect URL without auth token")

    # Update session with redirect info
    try:
        await BookingSessionService.update_session_data(
            chat_id,
            {
                "booking_stage": "redirected_to_ui",
                "redirect_url": redirect_url,
                "redirect_timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as e:
        logger.warning(f"Failed to update session with redirect info: {e}")

    return {
        "status": "redirect",
        "redirect_url": redirect_url,
        "selected_hotel": hotel_name,
        "selected_option": option_number,
        "message": f"Great choice! Click here to complete your booking for {hotel_name}.",
        "instruction": "Provide this link to the user so they can complete their booking.",
    }


__all__ = ["HotelSelectionInput", "select_hotel"]
