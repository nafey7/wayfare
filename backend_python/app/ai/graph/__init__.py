"""LangGraph-based AI agents for Voya.

This module provides LangGraph agents for travel booking conversations.
All routing is handled by the V2 Supervisor.

Usage:
    from app.ai.graph import invoke_supervisor_v2

    response = await invoke_supervisor_v2(
        message="fly from London to Paris next week",
        user_id=user.id,
        chat_id=chat_id,
    )
"""

from app.ai.graph.flight_graph import (
    cleanup_graph,
    get_flight_graph,
    invoke_flight_graph,
)
from app.ai.graph.hotel_graph import (
    cleanup_hotel_graph,
    get_hotel_graph,
    invoke_hotel_graph,
)
from app.ai.graph.itinerary_graph import (
    cleanup_itinerary_graph,
    get_itinerary_graph,
    invoke_itinerary_graph,
)
from app.ai.graph.state import (
    FlightParams,
    FlightState,
    HotelParams,
    HotelState,
    ItineraryParams,
    ItineraryState,
    SupervisorV2State,
)
from app.ai.graph.supervisor_v2 import (
    cleanup_supervisor_v2,
    get_supervisor_v2_graph,
    invoke_supervisor_v2,
)

__all__ = [
    "FlightParams",
    "FlightState",
    "HotelParams",
    "HotelState",
    "ItineraryParams",
    "ItineraryState",
    "SupervisorV2State",
    "cleanup_graph",
    "cleanup_hotel_graph",
    "cleanup_itinerary_graph",
    "cleanup_supervisor_v2",
    "get_flight_graph",
    "get_hotel_graph",
    "get_itinerary_graph",
    "get_supervisor_v2_graph",
    "invoke_flight_graph",
    "invoke_hotel_graph",
    "invoke_itinerary_graph",
    "invoke_supervisor_v2",
]
